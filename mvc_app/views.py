from __future__ import annotations

import html


def render_home_page(
    *,
    results: list[dict[str, str | float | int]] | None = None,
    query_name: str | None = None,
    error: str | None = None,
) -> str:
    error_block = ""
    if error:
        error_block = (
            '<div class="message error">'
            f"<strong>Ошибка:</strong> {html.escape(error)}"
            "</div>"
        )

    result_block = ""
    if results is not None:
        rows = []
        for item in results:
            rows.append(
                "<tr>"
                f"<td>{html.escape(str(item['name']))}</td>"
                f"<td>{html.escape(str(item['similarity']))}</td>"
                f"<td>{html.escape(str(item['confidence']))}</td>"
                f"<td class='path'>{html.escape(str(item['path']))}</td>"
                "</tr>"
            )
        result_block = (
            '<section class="results">'
            "<h2>Результаты поиска</h2>"
            f"<p class='hint'>Файл запроса: <strong>{html.escape(query_name or '')}</strong></p>"
            "<table>"
            "<thead><tr><th>Трек</th><th>Similarity</th><th>Confidence</th><th>Путь</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody>"
            "</table>"
            "</section>"
        )

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Audio Similarity Search</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4f1ea;
      --panel: rgba(255, 252, 247, 0.95);
      --ink: #1f1a17;
      --accent: #a44a3f;
      --accent-dark: #7f352d;
      --line: #d8c8b7;
      --muted: #6a5f55;
      --error: #8b1e2d;
      --error-bg: #f8e3e6;
    }}

    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(164, 74, 63, 0.18), transparent 28%),
        radial-gradient(circle at bottom right, rgba(121, 157, 115, 0.20), transparent 24%),
        linear-gradient(135deg, #efe5d3 0%, var(--bg) 48%, #f7f2eb 100%);
      min-height: 100vh;
    }}

    .shell {{
      width: min(980px, calc(100vw - 32px));
      margin: 32px auto;
      padding: 28px;
      border: 1px solid rgba(216, 200, 183, 0.9);
      border-radius: 24px;
      background: var(--panel);
      box-shadow: 0 18px 50px rgba(77, 49, 35, 0.12);
      backdrop-filter: blur(10px);
    }}

    h1 {{
      margin: 0 0 8px;
      font-size: clamp(30px, 4vw, 48px);
      line-height: 1.05;
    }}

    p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.6;
    }}

    .hero {{
      display: grid;
      gap: 12px;
      margin-bottom: 28px;
    }}

    .form-card {{
      margin-top: 22px;
      padding: 22px;
      background: linear-gradient(180deg, rgba(255,255,255,0.9), rgba(248, 241, 233, 0.95));
      border: 1px solid var(--line);
      border-radius: 20px;
    }}

    form {{
      display: grid;
      gap: 16px;
    }}

    label {{
      display: grid;
      gap: 8px;
      font-size: 15px;
      color: var(--ink);
    }}

    input[type="file"],
    input[type="number"] {{
      width: 100%;
      padding: 12px 14px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: #fffdfa;
      color: var(--ink);
      font-size: 15px;
    }}

    button {{
      width: fit-content;
      padding: 12px 22px;
      border: 0;
      border-radius: 999px;
      background: linear-gradient(135deg, var(--accent), #bd6a57);
      color: white;
      font-size: 15px;
      cursor: pointer;
      transition: transform 120ms ease, background 120ms ease;
    }}

    button:hover {{
      transform: translateY(-1px);
      background: linear-gradient(135deg, var(--accent-dark), var(--accent));
    }}

    .message {{
      margin: 0 0 18px;
      padding: 14px 16px;
      border-radius: 16px;
    }}

    .error {{
      color: var(--error);
      background: var(--error-bg);
      border: 1px solid rgba(139, 30, 45, 0.16);
    }}

    .results {{
      margin-top: 26px;
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 20px;
      background: rgba(255, 255, 255, 0.9);
    }}

    .results h2 {{
      margin: 0;
      padding: 18px 20px 6px;
      font-size: 24px;
    }}

    .hint {{
      padding: 0 20px 16px;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
    }}

    th, td {{
      padding: 14px 20px;
      border-top: 1px solid rgba(216, 200, 183, 0.7);
      text-align: left;
      vertical-align: top;
    }}

    th {{
      font-size: 13px;
      letter-spacing: 0.03em;
      text-transform: uppercase;
      color: var(--muted);
      background: rgba(244, 236, 225, 0.7);
    }}

    .path {{
      word-break: break-all;
      color: var(--muted);
      font-size: 14px;
    }}

    @media (max-width: 720px) {{
      .shell {{
        width: min(100vw - 18px, 100%);
        margin: 12px auto;
        padding: 18px;
      }}

      th, td {{
        padding: 12px 14px;
        font-size: 14px;
      }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <h1>Поиск похожих музыкальных композиций</h1>
      <p>Загрузи WAV-файл, и сервис найдёт самые похожие треки в подготовленной базе GTZAN.</p>
    </section>
    <section class="form-card">
      {error_block}
      <form action="/search-upload" method="post" enctype="multipart/form-data">
        <label>
          Выбери WAV-файл для анализа
          <input type="file" name="query_file" accept=".wav,audio/wav" required>
        </label>
        <label>
          Сколько результатов показать
          <input type="number" name="top_k" min="1" max="20" value="5">
        </label>
        <button type="submit">Найти похожие треки</button>
      </form>
    </section>
    {result_block}
  </main>
</body>
</html>"""
