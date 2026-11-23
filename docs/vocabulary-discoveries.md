# Vocabulary discoveries

The optional “Khám phá thêm” library contains 77 short Vietnamese articles for
97 vocabulary senses across 27 lessons: 37 senses in HSK1, 19 in HSK2 and 41 in
HSK3. The initial 23 November 2026 audit covered 94 senses (92 additions plus
the existing 你 and 饺子); the curiosity update adds three more senses. Not every
vocabulary word needs an article.

## Content and matching

The source of truth is
`frontend/src/features/lesson/data/vocabulary-discoveries.json`:

- `sources`: the publisher, HTTPS reference URL and source review date.
- `topics`: a short title, teaser, Vietnamese paragraph and supporting source IDs.
- `bindings`: the Hanzi, pinyin and Vietnamese meaning of each supported sense,
  its topic ID and the HSK/lesson where that sense was audited.

`vocabularyDiscoveries.ts` matches all three vocabulary fields, normalizing
Unicode, harmless whitespace and pinyin spacing. It does not attach articles by
Hanzi alone. Thus 家 meaning “home/family” has an article while 家 as a classifier
does not inherit that article. The money sense of 块 is handled separately from
its classifier senses. A newly edited meaning needs an explicit reviewed binding;
there is no guess-based fallback. HSK/lesson numbers document provenance rather
than restricting a matching sense to one lesson ID.

Related words may share an article (for example 你/您/你好 and the four grandparent
terms). Distinct subjects remain separate: 春节 and 春晚, 茶 and 奶茶, and individual
heritage sites. The article only appears on its vocabulary card; readings do not
repeat it. The prototype uses the same dumpling article and source as production.

## Editorial maintenance

Write one focused paragraph of about 30–90 Vietnamese whitespace-separated
tokens and a teaser short enough for the existing button. Use original phrasing,
verify specific claims against the linked page and record its review date. Prefer
institutions responsible for the subject: UNESCO, museums, universities, the
relevant city or education authority, transport operators and product publishers.
Dictionary sources support language explanations; learning scenarios are original
editorial examples. Describe regional customs with their scope rather than as
universal rules. Avoid invented origins, health promises, commercial superlatives
and time-sensitive fees, opening hours or admission requirements.

Some publishers block automated HTTP clients even though their indexed reference
pages are available. Review the actual supporting page, not an HTTP status alone.
Do not disable certificate checks or substitute an unrelated reference to make a
link checker pass. The Hainan source uses `en.hainan.gov.cn`; the older tourism
host returned a certificate mismatch during this review.

Essential word usage stays in the visible theory. Discoveries contain no questions,
scores, required completion action or AI generation at runtime. They do not
change lesson API DTOs, publication, pronunciation gates, the 80% practice threshold,
exam eligibility or existing learner data. Reading source details or opening a
popup introduces no additional progress request.

## Validation

The discovery tests compare every binding with the checked-in 40-lesson curriculum,
verify 37/19/41 coverage and source references, and test homographs, Unicode and
unknown meanings. Browser checks cover the real lesson layout, popup dismissal,
returning focus, source links and small screens. Keep the catalog and these
coverage expectations in sync when deliberately adding or removing articles.

## Verified curiosity update — 23 November 2026

Four existing articles now lead with a verified surprising fact: the panda's
wrist-bone pseudo-thumb, green/black tea from the same plant species, painted
terracotta warriors, and the transition from heavy coin strings to Song paper
money. Tea's social practices remain on 茶; the botanical story is on 绿茶.
Two new articles cover the lunisolar leap month (年 and 月) and the 福倒/福到
wordplay (到 meaning arrival, never its result-complement sense). They retain
one brief paragraph each, no quizzes and no completion requirements.

Each claim was checked against its specific reference: the Natural History
Museum of Los Angeles County, Kew, archaeologist Li Xiuzhen's Oxford article,
Columbia University, the Hong Kong Observatory, and Edinburgh's Confucius
Institute. The Fu article explains wordplay rather than asserting a historical
origin or a universal placement rule. The paper-money article avoids an
ambiguous claim about the first paper money of every kind. The Great Wall
space-visibility idea is deferred because 长城 is not an authored vocabulary
sense in the current curriculum; no lesson content is invented to host it.
