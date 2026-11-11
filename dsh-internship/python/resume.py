"""Extract local resume text and conservative, labelled profile suggestions. No model call."""
import base64
from io import BytesIO
from pathlib import Path
import re
import sys
from xml.etree import ElementTree
from zipfile import ZipFile, BadZipFile


def labelled(text, labels):
    for line in text.splitlines():
        found = re.match(r'^\s*(?:' + '|'.join(labels) + r')\s*[:：]\s*(.+)$', line)
        if found:
            return found.group(1).strip()
    return ''


def suggestions(text):
    value = {}
    stage = labelled(text, ['学历与年级', '学历', '年级'])
    if stage:
        value['stage'] = stage[:4000]
    extra = labelled(text, ['其他不可妥协条件', '其他重要条件', '补充条件'])
    if extra:
        value['additional_constraints'] = extra[:4000]
    mapping = {'skills_known': ['已掌握技能', '已掌握', '专业技能', '技术技能'],
               'skills_learning': ['正在学习', '在学技能'],
               'cities': ['目标城市', '意向城市', '求职城市'],
               'keywords': ['求职意向', '意向岗位', '目标岗位'],
               'priorities': ['最看重的条件', '求职偏好']}
    for key, labels in mapping.items():
        raw = labelled(text, labels)
        if raw:
            value[key] = list(dict.fromkeys(item.strip()[:500] for item in re.split(r'[,，、;；]+', raw) if item.strip()))[:40]
    # Availability is accepted only when explicitly stated with a unit.
    days = re.search(r'(?:每周可出勤|每周出勤|每周到岗)\s*[:：]?\s*([1-7])\s*天', text)
    months = re.search(r'(?:可连续实习|可实习时长|实习时长)\s*[:：]?\s*(\d{1,3})\s*个?月', text)
    if days:
        value['days_per_week'] = int(days.group(1))
    if months and 0 < int(months.group(1)) <= 120:
        value['months'] = int(months.group(1))
    return value


def import_resume(request):
    if not isinstance(request, dict) or set(request) != {'name', 'data'} or not isinstance(request['name'], str) or not isinstance(request['data'], str):
        raise ValueError('简历请求格式不正确')
    try:
        data = base64.b64decode(request['data'], validate=True)
    except ValueError:
        raise ValueError('简历文件编码不正确') from None
    if not 0 < len(data) <= 4 * 1024 * 1024:
        raise ValueError('请选择 4 MB 以内的简历文件')
    extension = Path(request['name']).suffix.lower()
    if extension in ('.txt', '.md'):
        try:
            text = data.decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                text = data.decode('gb18030')
            except UnicodeDecodeError:
                raise ValueError('无法识别文字编码，请另存为 UTF-8 文本') from None
    elif extension == '.docx':
        try:
            with ZipFile(BytesIO(data)) as archive:
                info = archive.getinfo('word/document.xml')
                if info.file_size > 2 * 1024 * 1024:
                    raise ValueError('Word 文档正文过大')
                xml = archive.read(info)
            if b'<!DOCTYPE' in xml.upper() or b'<!ENTITY' in xml.upper():
                raise ValueError('不支持该 Word 文档格式')
            document = ElementTree.fromstring(xml)
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            text = '\n'.join(''.join(paragraph.itertext()) for paragraph in document.findall('.//w:p', ns))
        except (BadZipFile, KeyError, ElementTree.ParseError):
            raise ValueError('无法读取 DOCX，请检查文件或另存为文本') from None
    elif extension == '.pdf':
        # Optional libraries live under this plugin, never in the original Agent.
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '.runtime' / 'python'))
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ValueError('尚未安装 PDF 读取依赖，请安装 requirements-resume.txt，或上传 DOCX / TXT') from None
        try:
            reader = PdfReader(BytesIO(data))
            if reader.is_encrypted:
                raise ValueError('请先移除 PDF 密码，或改用 DOCX / TXT')
            if len(reader.pages) > 10:
                raise ValueError('请上传 10 页以内的简历')
            text = '\n'.join(page.extract_text() or '' for page in reader.pages)
        except ValueError:
            raise
        except Exception:
            raise ValueError('无法读取 PDF，请改用 DOCX / TXT') from None
    else:
        raise ValueError('支持 PDF、DOCX、TXT、MD；暂不支持图片或旧版 DOC')
    text = text.strip()
    if len(text) < 10:
        raise ValueError('未提取到足够文字；扫描件或图片简历请改用可复制文字的文档，当前没有 OCR')
    if len(text) > 60000:
        raise ValueError('简历文字过多，请精简后上传')
    return {'text': text, 'suggestions': suggestions(text),
            'notice': '仅按明确的中文字段提取，可能遗漏；未推断未写明的信息，也未修改正式档案。'}
