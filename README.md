# tofrom-time

旅費精算用の経路表示 CLI。Yahoo!乗換案内をもとに、出発駅・到着駅・時刻（出発 or 到着）を
指定して経路を 1 行テキストで出力し、選択ルートの印刷ページを PDF 証憑として保存できる。

```text
分倍河原(13:26)→笹塚(13:32)→…→成田空港(東京)(15:37)
```

> [!IMPORTANT]
> 本ツールは Yahoo!乗換案内の Web ページを **スクレイピング** して動作します。
> **個人利用の範囲** でのみ使用してください。詳細は[注意事項・免責](#注意事項免責)を参照。

## セットアップ

```bash
uv sync
uv run playwright install chromium   # PDF 保存を使う場合のみ
```

## 使い方

```bash
# 到着時刻指定
uv run tofrom-time --from 分倍河原 --to 成田空港 --arrive 14:43

# 出発時刻指定（駅の別名・日付指定も可）
uv run tofrom-time --from mizonokuchi --to haneda --depart 09:00 --date 2026-07-17

# 候補を選んで PDF 保存
uv run tofrom-time --from 分倍河原 --to 成田空港 --arrive 14:43 --pick 1 --pdf ./out/
```

主なオプション: `--depart`/`--arrive`（排他）, `--date`, `--pick`, `--json`,
`--prefer NAME`, `--all`, `--no-cache`, `--pdf DIR`。

## ルート選択条件

`config/stations.toml` の `[preferences.<行き先>]` で、行き先ごとに使いたい列車や経由を定義する
（行き先名が一致すると自動適用、`--all` で無効化）。

- `any_lines` / `via`: 指定路線を含む・指定駅を通るルートに絞る（ハード）
- `deny_lines`: 指定路線を使うルートを除外（ハード）
- `prefer_lines`: 指定路線を含むルートを上位に並べる（ソフト）
- `use_limited_express`: 有料特急（スカイライナー/NEX 等）を候補へ含める

`[defaults]` に書いた条件は全行き先に適用される。条件に合うルートが 0 件なら全候補へフォールバックする。

## 開発

```bash
uv run pytest            # テスト
uv run pytest --cov      # カバレッジ
```

パーサのテストは `tests/fixtures/` の保存済み HTML に対して行い、ネットワークに依存しない。
詳細な設計方針と Yahoo の仕様調査結果は [CLAUDE.md](CLAUDE.md) を参照。

## 注意事項・免責

本ツールは Yahoo!乗換案内（`https://transit.yahoo.co.jp`）が公式の経路検索 API を
提供していないため、検索結果ページを **スクレイピング** して経路を取得します。
利用にあたっては以下を順守してください。

- **個人利用の範囲に限定**してください。大量・高頻度のアクセスや、商用・再配布を目的とした
  自動収集には使用しないでください。
- リクエストには **適切な間隔（スリープ）** を入れ、**User-Agent を明示** しています。
  取得結果は **キャッシュ** し、同一クエリの再取得を避けます（`--no-cache` で無効化）。
- Yahoo! の **利用規約・robots.txt を尊重** してください。サイト側の HTML 構造変更により
  いつでも動作しなくなる可能性があります。
- 本ツールは Yahoo Japan 株式会社（LINEヤフー株式会社）とは **一切関係のない非公式ツール** です。
- 本ツールの利用によって生じたいかなる損害についても、作者は責任を負いません。
  取得した情報の正確性も保証されません（**経費精算等では必ず原典を確認**してください）。

## ライセンス

[MIT License](LICENSE) © 2026 Shigeya Suzuki
