"""只读网页工具：公开 HTTPS、固定 DNS 地址、robots 检查、有限响应。"""
import http.client
import ipaddress
import json
import re
import socket
import ssl
from html.parser import HTMLParser
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

from .core import now
from .http import NetworkError, request_json

USER_AGENT = "InternshipRadar/1.0"
MAX_BYTES = 2_000_000
MAX_TEXT = 80_000


def public_url(value):
    if not isinstance(value, str) or len(value) > 2048 or re.search(r"[\s\\\x00-\x1f\x7f]", value):
        raise ValueError("网址无效。")
    try:
        p = urlsplit(value)
        if (p.scheme != "https" or not p.hostname or p.username or p.password
                or p.port not in (None, 443)):
            raise ValueError()
        host = p.hostname.encode("idna").decode("ascii").lower()
        if host == "localhost" or host.endswith((".local", ".localhost", ".internal")):
            raise ValueError()
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            raise ValueError()
        authority = f"[{host}]" if ":" in host else host
        return urlunsplit(("https", authority, p.path or "/", p.query, ""))
    except (ValueError, UnicodeError):
        raise ValueError("只允许不含凭据的公开 HTTPS 地址和默认端口。") from None


def public_addresses(host):
    try:
        addresses = list(dict.fromkeys(row[4][0] for row in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)))
        # 某些本机代理使用 198.18.0.0/15 作为 Fake-IP。绝不连接这些虚拟地址；
        # 改向固定的公共 DNS HTTPS 地址查询，再验证并固定真实 IP。
        fake_network = ipaddress.ip_network("198.18.0.0/15")
        if addresses and all(ipaddress.ip_address(ip) in fake_network for ip in addresses):
            addresses = public_dns(host)
        if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
            raise ValueError("网址解析到非公开网络，已拒绝。")
        return addresses
    except OSError:
        raise NetworkError("网页域名解析失败。") from None


class PinnedHTTPS(http.client.HTTPSConnection):
    """连接刚检查过的 IP；TLS 仍验证原域名，避免检查后再次解析 DNS。"""
    def __init__(self, host, address):
        super().__init__(host, timeout=15, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        sock = socket.create_connection((self.address, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except BaseException:
            sock.close()
            raise


def public_dns(host):
    connection = PinnedHTTPS("cloudflare-dns.com", "1.1.1.1")
    try:
        connection.request("GET", "/dns-query?" + urlencode({"name": host, "type": "A"}),
                           headers={"Accept": "application/dns-json", "User-Agent": USER_AGENT})
        response = connection.getresponse()
        raw = response.read(65537)
        if response.status != 200 or len(raw) > 65536:
            raise ValueError()
        result = json.loads(raw)
        if result.get("Status") != 0:
            raise ValueError()
        return [row["data"] for row in result.get("Answer", []) if row.get("type") == 1]
    except (ValueError, KeyError, TypeError, OSError, http.client.HTTPException):
        raise NetworkError("检测到代理虚拟 DNS，但公共 DNS 查询失败；请关闭代理的 Fake-IP 模式后重试。") from None
    finally:
        connection.close()


def fetch_public(url):
    url = public_url(url)
    p = urlsplit(url)
    address = public_addresses(p.hostname)[0]
    connection = PinnedHTTPS(p.hostname, address)
    try:
        connection.request("GET", urlunsplit(("", "", p.path, p.query, "")), headers={
            "User-Agent": USER_AGENT, "Accept": "text/html,text/plain;q=0.9", "Accept-Encoding": "identity"})
        response = connection.getresponse()
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("网页超过 2 MB 限制。")
        return response.status, dict((k.lower(), v) for k, v in response.getheaders()), raw
    except (OSError, http.client.HTTPException):
        raise NetworkError("网页连接失败或超时。") from None
    finally:
        connection.close()


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.links, self.title_parts = [], [], []
        self.hidden = 0
        self.in_title = False
        self.anchor = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "style", "noscript", "template", "svg"}:
            self.hidden += 1
        if self.hidden:
            return
        if tag == "title":
            self.in_title = True
        if tag == "a" and attrs.get("href"):
            self.anchor = [attrs["href"], []]
        if tag in {"p", "div", "li", "br", "h1", "h2", "h3", "tr", "section"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "template", "svg"}:
            self.hidden = max(0, self.hidden - 1)
        if self.hidden:
            return
        if tag == "title":
            self.in_title = False
        if tag == "a" and self.anchor:
            self.links.append((self.anchor[0], "".join(self.anchor[1]).strip()[:160]))
            self.anchor = None
        if tag in {"p", "div", "li", "h1", "h2", "h3", "tr", "section"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)
            if self.in_title:
                self.title_parts.append(data)
            if self.anchor:
                self.anchor[1].append(data)


def extract_page(raw, headers, url):
    content_type = headers.get("content-type", "").lower()
    if not any(kind in content_type for kind in ("text/html", "application/xhtml+xml", "text/plain")):
        raise ValueError("只读取 HTML 或纯文本；不支持 PDF、下载文件或此响应类型。")
    charset = re.search(r"charset=[\"']?([\w-]+)", content_type)
    if charset is None:
        charset = re.search(rb"charset=[\"']?([\w-]+)", raw[:4096], re.I)
    encoding = charset.group(1) if charset else "utf-8"
    if isinstance(encoding, bytes):
        encoding = encoding.decode("ascii")
    try:
        html = raw.decode(encoding, errors="replace")
    except LookupError:
        html = raw.decode("utf-8", errors="replace")
    parser = PageParser()
    if "text/plain" in content_type:
        text, title = html, ""
    else:
        parser.feed(html)
        text, title = "".join(parser.parts), "".join(parser.title_parts).strip()[:300]
    text = "\n".join(line.strip() for line in re.sub(r"[^\S\n]+", " ", text).splitlines() if line.strip())
    text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", text)
    if len(text) < 40:
        raise ValueError("页面正文不足，可能需要 JavaScript、登录或验证码；不能当作已读岗位。")
    links, seen = [], set()
    for href, label in parser.links:
        try:
            link = public_url(urljoin(url, href))
        except ValueError:
            continue
        if link not in seen:
            links.append({"url": link, "label": label})
            seen.add(link)
        if len(links) >= 200:
            break
    return {"url": url, "title": title, "text": text[:MAX_TEXT], "links": links,
            "truncated": len(text) > MAX_TEXT, "fetched_at": now()}


class WebTools:
    def __init__(self, search_key=""):
        self.search_key = search_key
        self.robots = {}

    @property
    def search_available(self):
        return bool(self.search_key)

    def search(self, query):
        if not self.search_key:
            raise ValueError("未配置 TAVILY_API_KEY；请阅读已有岗位、种子链接或已发现的链接。")
        result = request_json("https://api.tavily.com/search", api_key=self.search_key, payload={
            "query": query, "search_depth": "basic", "max_results": 5,
            "include_answer": False, "include_raw_content": False, "auto_parameters": False}, timeout=20)
        if not isinstance(result, dict) or not isinstance(result.get("results"), list):
            raise NetworkError("搜索服务响应格式错误。")
        rows = []
        for item in result["results"][:5]:
            if not isinstance(item, dict):
                continue
            try:
                url = public_url(item.get("url"))
            except ValueError:
                continue
            rows.append({"url": url, "title": str(item.get("title", ""))[:300],
                         "snippet": str(item.get("content", ""))[:1000]})
        return {"results": rows, "warning": "搜索摘要只是线索，不能作为已核实的岗位证据。"}

    def allowed(self, url):
        p = urlsplit(url)
        origin = urlunsplit((p.scheme, p.netloc, "", "", ""))
        if origin not in self.robots:
            status, headers, raw = fetch_public(origin + "/robots.txt")
            parser = RobotFileParser()
            if status == 404:
                parser.parse([])
            elif status == 200 and "text/html" not in headers.get("content-type", ""):
                parser.parse(raw.decode("utf-8", errors="replace").splitlines())
            else:
                raise ValueError("无法确认 robots.txt 规则，暂不读取此网站。")
            self.robots[origin] = parser
        if not self.robots[origin].can_fetch(USER_AGENT, url):
            raise ValueError("网站 robots.txt 不允许读取此路径。")

    def read(self, url):
        url = public_url(url)
        for _ in range(4):
            self.allowed(url)
            status, headers, raw = fetch_public(url)
            if status in (301, 302, 303, 307, 308):
                location = headers.get("location")
                if not location:
                    raise ValueError("网页重定向没有目标。")
                url = public_url(urljoin(url, location))
                continue
            if status != 200:
                raise ValueError(f"网页 HTTP {status}；需要登录、限流或失效时换来源，不绕过。")
            return extract_page(raw, headers, url)
        raise ValueError("网页重定向次数超过限制。")
