"""Parse Colab execution outputs into Flet controls for display."""

import flet as ft

from components.ansi_parser import parse_ansi_to_flet_text
from core import theme, tokens


def parse_outputs_to_controls(outputs: list) -> list[ft.Control]:
    """Convert raw Colab output dicts into renderable Flet controls."""
    output_controls = []
    for out in outputs:
        if len(output_controls) >= 1000:
            break
        otype = out.get("output_type") or out.get("type", "")
        if otype == "stream":
            is_err = out.get("name") == "stderr"
            text = out.get("text", "")
            output_controls.append(
                parse_ansi_to_flet_text(
                    raw_text=text, default_size=tokens.FONT_SM, is_error=is_err
                )
            )
        elif otype == "error":
            traceback = "\n".join(out.get("traceback", []))
            output_controls.append(
                parse_ansi_to_flet_text(
                    raw_text=traceback,
                    default_size=tokens.FONT_SM,
                    is_error=True,
                )
            )
        elif otype in ["execute_result", "display_data"]:
            data = out.get("data", {})
            if "image/png" in data:
                try:
                    b64_img = data["image/png"]
                    b64_img = b64_img.replace("\n", "").replace("\r", "")
                    output_controls.append(
                        ft.Container(
                            content=ft.Image(
                                src_base64=b64_img,
                                fit=ft.BoxFit.CONTAIN,
                            ),
                            margin=ft.Margin(0, tokens.SPACE_XS, 0, tokens.SPACE_XS),
                            border_radius=tokens.RADIUS_SM,
                        )
                    )
                except Exception as e:
                    output_controls.append(
                        ft.Text(f"Image Error: {e}", color=theme.ERROR)
                    )
            elif "text/plain" in data:
                output_controls.append(
                    parse_ansi_to_flet_text(
                        raw_text=data["text/plain"],
                        default_size=tokens.FONT_SM,
                    )
                )
    return output_controls
