from __future__ import annotations

from pathlib import Path

from .engine import BacktestResult


def save_equity_curve_svg(
    result: BacktestResult,
    output_path: str | Path,
    *,
    title: str = "Equity Curve",
) -> str:
    resolved_path = Path(output_path).resolve()
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text(_build_equity_curve_svg(result, title=title), encoding="utf-8")
    return str(resolved_path)


def _build_equity_curve_svg(result: BacktestResult, *, title: str) -> str:
    width = 960
    height = 540
    margin_left = 84
    margin_right = 32
    margin_top = 64
    margin_bottom = 64
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom

    items = sorted(result.equity_curve.items())
    if not items:
        items = [("N/A", 1.0)]
    dates = [item[0] for item in items]
    values = [float(item[1]) for item in items]
    min_value = min(values)
    max_value = max(values)
    if min_value == max_value:
        min_value -= 0.05
        max_value += 0.05
    value_span = max_value - min_value

    def x_pos(index: int) -> float:
        if len(values) == 1:
            return margin_left + (plot_width / 2.0)
        return margin_left + (plot_width * index / (len(values) - 1))

    def y_pos(value: float) -> float:
        return margin_top + plot_height - ((value - min_value) / value_span) * plot_height

    polyline_points = " ".join(f"{x_pos(idx):.2f},{y_pos(value):.2f}" for idx, value in enumerate(values))
    latest_date = dates[-1]
    latest_value = values[-1]
    cumulative_return = result.cumulative_return * 100.0
    y_ticks = [min_value + value_span * step / 4.0 for step in range(5)]
    x_tick_indices = sorted({0, len(dates) - 1, len(dates) // 2})

    y_grid = "\n".join(
        (
            f'<line x1="{margin_left}" y1="{y_pos(tick):.2f}" x2="{margin_left + plot_width}" '
            f'y2="{y_pos(tick):.2f}" stroke="#d7dee9" stroke-width="1" />'
            f'<text x="{margin_left - 12}" y="{y_pos(tick) + 5:.2f}" text-anchor="end" '
            f'font-size="12" fill="#4a5568">{tick:.3f}</text>'
        )
        for tick in y_ticks
    )
    x_labels = "\n".join(
        (
            f'<line x1="{x_pos(idx):.2f}" y1="{margin_top + plot_height}" x2="{x_pos(idx):.2f}" '
            f'y2="{margin_top + plot_height + 6}" stroke="#4a5568" stroke-width="1" />'
            f'<text x="{x_pos(idx):.2f}" y="{margin_top + plot_height + 26}" text-anchor="middle" '
            f'font-size="12" fill="#4a5568">{dates[idx]}</text>'
        )
        for idx in x_tick_indices
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#f8fafc" />
  <text x="{margin_left}" y="34" font-size="24" font-family="Segoe UI, Arial, sans-serif" fill="#0f172a">{_xml_escape(title)}</text>
  <text x="{margin_left}" y="56" font-size="13" font-family="Segoe UI, Arial, sans-serif" fill="#475569">Latest: {latest_date} | Equity: {latest_value:.4f} | Cumulative Return: {cumulative_return:.2f}%</text>
  <rect x="{margin_left}" y="{margin_top}" width="{plot_width}" height="{plot_height}" fill="#ffffff" stroke="#cbd5e1" stroke-width="1" rx="10" />
  {y_grid}
  <line x1="{margin_left}" y1="{margin_top + plot_height}" x2="{margin_left + plot_width}" y2="{margin_top + plot_height}" stroke="#475569" stroke-width="1.5" />
  {x_labels}
  <polyline fill="none" stroke="#0f766e" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" points="{polyline_points}" />
  <circle cx="{x_pos(len(values) - 1):.2f}" cy="{y_pos(latest_value):.2f}" r="5" fill="#0f766e" />
</svg>
"""


def _xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
