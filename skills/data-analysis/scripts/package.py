"""제출·업로드용 zip 두 벌을 만든다.

    python scripts/package.py

**두 벌이 필요한 이유 — 요구하는 구조가 다르다.**

    타임리      .pi/skills/<name>/SKILL.md      ← 플랫폼이 이 경로를 찾는다
    대회 제출   skills/data-analysis/skill.md   ← 공지가 이 구조를 지정했다

같은 파일을 두 껍데기에 담는다. 내용은 하나뿐이므로 어긋날 일이 없다.

🔴 인증키가 섞이지 않았는지 담기 전에 확인한다 — 참가 서약의 보안 조항이다.
"""
from __future__ import annotations

import re
import sys
import zipfile
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from api import use_utf8_stdout   # noqa: E402
import paths                      # noqa: E402

SKILL = paths.SKILL
DIST = SKILL.parent.parent / "dist"
NAME = "trusted-procurement-agent"

# 담을 것 — 실행에 필요한 것만. 산출물·상태는 담지 않는다
포함 = ["SKILL.md", "AGENT.md", "README.md", "skill.md",
       "reference", "config", "scripts", "templates", "examples",
       "sample-data", "tests"]
# 🔴 `.PARTIAL.json` 과 `.tmp` 는 **절대 담지 않는다.** 반쪽 수집본이
#    동봉 스냅샷 자리에 섞이면 심사자가 그것으로 판정하게 된다.
제외패턴 = re.compile(
    r"(__pycache__|\.pyc$|/state/|/output/|\.DS_Store|\.PARTIAL\.json$|\.tmp$)")

# 🔴 이 표현이 파일에 있으면 담지 않고 멈춘다
위험 = re.compile(r"(serviceKey=[A-Za-z0-9%]{20,}|DATAGO_KEY\s*=\s*['\"][^'\"]{20,})")


def 담을파일들() -> list[pathlib.Path]:
    파일: list[pathlib.Path] = []
    for 이름 in 포함:
        대상 = SKILL / 이름
        if not 대상.exists():
            continue
        if 대상.is_file():
            파일.append(대상)
            continue
        for f in 대상.rglob("*"):
            if f.is_file() and not 제외패턴.search(f.as_posix()):
                파일.append(f)
    return sorted(set(파일))


def 원본거르기(파일들: list[pathlib.Path]) -> tuple[list[pathlib.Path],
                                                list[pathlib.Path]]:
    """🔴 **슬림본이 있는 원본은 담지 않는다.**

    zip 은 4.7MB 인데 **풀면 53MB** 였고, 그중 50.5MB 가 `retail.json` 과
    `wholesale.json` 원본이었다. 그런데 이 둘은 **런타임에 한 번도 읽히지
    않는다** — `paths.어디에()` 가 같은 위치의 `_slim` 을 먼저 잡는다.
    (`origin.json` 은 이미 없는 채로 전 과정이 통과한다.)

    타임리는 `.pi/skills/` 를 **매 턴 지우고 다시 만든다.** 읽지도 않을
    50MB 를 매 턴 펼치는 값을 치를 이유가 없다.

    🔴 이름으로 짝을 찾는다 — 「슬림본이 없는 원본」은 그대로 담는다.
       새 소스를 넣고 슬림을 안 만들면 원본이 자동으로 들어가므로,
       규칙이 조용히 자료를 빠뜨리지 않는다.

    잃는 것은 하나 — 심사자가 `slim.py` 로 슬림본을 다시 만드는 길이다.
    그건 어차피 자기 키로 재수집해야 하는 작업이라 원본이 있어도 못 한다.
    """
    슬림보유 = {f.name.split("_slim")[0] for f in 파일들 if "_slim" in f.name}
    남김, 뺀것 = [], []
    for f in 파일들:
        원본임 = (f.parent.name == "sample-data" and "_slim" not in f.name
               and f.name.split(".")[0] in 슬림보유)
        (뺀것 if 원본임 else 남김).append(f)
    return 남김, 뺀것


def 키검사(파일들: list[pathlib.Path]) -> list[str]:
    """텍스트 파일에 인증키가 박혀 있지 않은지 본다."""
    걸림: list[str] = []
    for f in 파일들:
        if f.suffix.lower() not in {".py", ".md", ".json", ".csv", ".html", ".css"}:
            continue
        try:
            내용 = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:                                  # noqa: BLE001
            continue
        if 위험.search(내용):
            걸림.append(str(f.relative_to(SKILL)))
    return 걸림


def 만들기(파일들: list[pathlib.Path], 이름: str, 접두: str) -> pathlib.Path:
    DIST.mkdir(parents=True, exist_ok=True)
    경로 = DIST / 이름
    with zipfile.ZipFile(경로, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in 파일들:
            z.write(f, f"{접두}/{f.relative_to(SKILL).as_posix()}")
    return 경로


필수 = ["SKILL.md", "AGENT.md", "README.md",
      "reference/item_map.csv", "config/settings.json",
      "scripts/agent.py", "scripts/run.py", "templates/report.html"]


def 필수검사() -> list[str]:
    """🔴 **형식 누락은 내용과 무관하게 탈락이다.**

    1차 심사가 필수 제출물 여부를 기계적으로 스크리닝한다. 조용히 빠진 파일이
    있으면 그대로 나간다. 담기 전에 막는다.
    """
    return [f for f in 필수 if not (SKILL / f).exists()]


def main() -> None:
    use_utf8_stdout()
    빠짐 = 필수검사()
    if 빠짐:
        print("🔴 필수 파일이 없습니다. 담지 않고 멈춥니다:")
        for f in 빠짐:
            print(f"   {f}")
        raise SystemExit(1)
    print(f"  필수 파일 {len(필수)}개 확인")

    파일들, 뺀것 = 원본거르기(담을파일들())
    print(f"담을 파일 {len(파일들)}개")
    for f in 뺀것:
        print(f"  제외 {f.name:26} {f.stat().st_size/1e6:>5.1f}MB"
              f" — 슬림본이 있어 런타임에 읽히지 않습니다")

    걸림 = 키검사(파일들)
    if 걸림:
        print("\n🔴 인증키로 보이는 문자열이 있습니다. 담지 않고 멈춥니다:")
        for f in 걸림:
            print(f"   {f}")
        raise SystemExit(1)
    print("  인증키 검사 통과")

    a = 만들기(파일들, f"{NAME}-timely.zip", f".pi/skills/{NAME}")
    b = 만들기(파일들, "2026_Upstage_BDAI_Skill_CPAI.zip", "skills/data-analysis")

    for z in (a, b):
        print(f"  → {z.relative_to(DIST.parent)}  {z.stat().st_size/1e6:.1f}MB")
    print("\n  타임리    .pi/skills/ 구조 — 업로드 후 commit_skill 호출 필요")
    print("  대회 제출  skills/data-analysis/ 구조")


if __name__ == "__main__":
    main()
