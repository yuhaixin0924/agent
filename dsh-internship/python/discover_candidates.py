"""Run fixed searches without an LLM; credentials only from explicit env/file."""
import argparse
from contextlib import closing
import os
from pathlib import Path
from bridge import Backend
from candidates import Candidates
from agent_snapshot.web import WebTools


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', required=True)
    parser.add_argument('--search-env', type=Path, help='Explicit dotenv file; reads only TAVILY_API_KEY')
    parser.add_argument('--mode', choices=('baseline', 'profile'), default='baseline')
    parser.add_argument('--max-pages', type=int, choices=range(1, 31), default=10)
    args = parser.parse_args()
    key = os.environ.get('TAVILY_API_KEY', '').strip()
    if not key and args.search_env:
        for line in args.search_env.read_text().splitlines():
            name, sep, value = line.strip().partition('=')
            if sep and name.strip() == 'TAVILY_API_KEY':
                key = value.strip().strip('\"\'')
    web = WebTools(key)
    with closing(Backend(args.data_dir)) as backend:
        queue = Candidates(backend)
        queries = queue.plan(mode=args.mode)['queries']
        for query in queries:
            print('搜索：' + query, flush=True)
            try:
                response = web.search(query)
                queue.add(query, [r['url'] for r in response['results']])
            except Exception as exc:
                queue.add(query, [], str(exc) if isinstance(exc, ValueError) else type(exc).__name__)
            queue.report()  # Persist progress even if later requests fail.
        for row in [r for r in queue.rows() if r['screening'] == 'unread'][:args.max_pages]:
            print('读取：' + row['url'], flush=True)
            queue.check(row['id'], web)
            queue.report()
        result = queue.report()
        print(result['counts'])
        print(result['acceptance'])
        print('报告目录：' + str(backend.root))
        return 1 if any(s['error'] for s in result['searches'][-len(queries):]) else 0


if __name__ == '__main__':
    raise SystemExit(main())
