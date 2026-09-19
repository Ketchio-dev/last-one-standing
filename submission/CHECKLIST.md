# 제출 체크리스트 — UnivaBio 2026

마감 **2026-10-06 23:45 EDT**. 규정: **user interaction 있는 프로토타입** + 데모 영상 +
**1쪽 PDF** + 저장소. 심사 Idea & Innovation · Implementation · **Health Impact & Rigor** ·
Design & Usability · Presentation.

> 심사 기준에 이 문장이 그대로 있다: **"Is the team honest about what's finished versus planned?"**
> 그래서 devpost 본문과 1쪽 PDF 둘 다 "Finished vs planned" 절을 따로 뒀다. 지우지 마라.

## 1. 제출 전 저장소 확인

- [ ] 새 폴더에 클론해서 `python3 src/build.py && python3 src/report.py &&
      python3 src/export_web.py` 가 그대로 돈다 (데이터가 커밋돼 있어야 한다)
- [ ] `python3 src/check.py` → **25/25**
- [ ] `python3 src/sabotage.py` → **25/25 검출, 놓침 0**
- [ ] `web/index.html` 을 **더블클릭**해서 열린다 (서버 없이)
- [ ] **분자를 눌러 보면 1996→2026 공급자 밴드가 뜬다** — "user interaction 있는 프로토타입"
      요건이 이것이다. 안 되면 규정 미충족이다

## 2. 1쪽 PDF (별도 제출물)

- [ ] `submission/onepager.pdf` — 이미 만들어 뒀다. **한 쪽인지 다시 확인**
- [ ] 내용을 고쳤으면 다시 뽑는다:
      `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless
       --no-pdf-header-footer --print-to-pdf=onepager.pdf file://$PWD/onepager.html`
- [ ] 흑백으로 인쇄해도 표가 읽히는지 (심사위원이 종이로 볼 수 있다)

## 3. 영상

- [ ] `_workflow/video/hackathon-video/out/last-one-standing.mp4` — **3:15**
- [ ] **끝까지 본다.** 검사가 못 보는 것: 말투, 그림이 말과 맞는지
- [ ] 업로드 (YouTube 또는 Vimeo). **게시는 사람이 한다**
- [ ] 공개 범위 확인

## 4. Devpost 폼

- [ ] tagline — `devpost.md` 의 A/B/C 중 택 1
- [ ] 본문 — `devpost.md` 붙여넣기 (맨 위 안내 블록은 지운다)
- [ ] **Inspiration 을 사람이 채웠는지 확인.** 비어 있으면 제출하지 않는다
- [ ] 저장소 링크 · 영상 링크 · 1쪽 PDF 첨부
- [ ] 라이브 링크 (GitHub Pages 로 `web/` 게시)

## 5. 사람만 할 수 있는 것

- [ ] Inspiration 문단
- [ ] tagline 택 1
- [ ] 영상 시청 후 업로드
- [ ] 저장소 커밋·푸시
- [ ] 제출 버튼
- [ ] (선택) healthproductshortages.ca 무료 계정 — 계정 생성은 내가 못 한다.
      없어도 제출에는 지장 없다. 있으면 품절 실측을 덧댈 수 있다

## 6. 제출 후

- [ ] 제출물 링크가 로그아웃 상태에서 열리는지 확인
- [ ] 마감 전까지는 몇 번이든 고칠 수 있다
