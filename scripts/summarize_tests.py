"""Print a compact GitHub job summary from pytest or Node JUnit output."""
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def summarize(path):
    root = ET.parse(path).getroot()
    cases = list(root.iter('testcase'))
    failed = sum(c.find('failure') is not None or c.find('error') is not None for c in cases)
    skipped = sum(c.find('skipped') is not None for c in cases)
    print(f'### {Path(path).stem}')
    print('| Collected | Passed | Failed/error | Skipped |')
    print('| ---: | ---: | ---: | ---: |')
    print(f'| {len(cases)} | {len(cases) - failed - skipped} | {failed} | {skipped} |')
    print('\nDownload the XML from this workflow run’s **Artifacts** for individual test results.')
    return 0 if cases else 1


if __name__ == '__main__':
    if not Path(sys.argv[1]).is_file():
        print('No test report was produced. Inspect the setup and test steps; this is not a passing run.')
        raise SystemExit(1)
    raise SystemExit(summarize(sys.argv[1]))
