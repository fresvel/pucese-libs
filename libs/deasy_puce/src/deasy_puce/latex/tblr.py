import pandas as pd

class LatexTblr:
    def __init__(
        self,
        width="\\textwidth",
        font_size="\\footnotesize",
        header_color="colhead!40",
        set_caption="default"
    ):
        self.width = width
        self.font_size = font_size
        self.header_color = header_color
        self.set_caption = set_caption

    def from_dataframe(self,df,caption,label,h_align=None,v_align=None,scale=None):
        n_cols = df.shape[1]

        if h_align is None:
            h_align = [
                "c" if pd.api.types.is_numeric_dtype(df[col]) else "j"
                for col in df.columns
            ]

        if v_align is None:
            v_align = ["m"] * n_cols

        if scale is None:
            scale = [1] * n_cols

        colspec = self._build_colspec(h_align, v_align, scale)
        headers = self._build_headers(df)
        body = self._build_body(df)

        return self._render(caption, label, colspec, headers, body)

    
    def _build_colspec(self, h, v, s):
        if not (len(h) == len(v) == len(s)):
            raise ValueError("Configuración de columnas inconsistente")
        return " ".join(
            f"X[{h[i]},{v[i]},{s[i]}]"
            for i in range(len(s))
        )

    def _build_headers(self, df):
        return " & ".join(map(str, df.columns)) + r" \\"

    def _build_body(self, df):
        return "\n".join(
            " & ".join(map(str, row.values)) + r" \\"
            for _, row in df.iterrows()
        )

    def _render_set_caption(self):
        return rf"""
        \SetTblrTemplate{{caption}}{{{self.set_caption}}}
        """

    def _render(self, caption, label, colspec, headers, body):
        caption_tpl = self._render_set_caption()

        return rf"""
        {caption_tpl}\begin{{longtblr}}[
        caption={{{caption}}},
        label={{tab:{label}}}
        ]{{ 
        colspec={{{colspec}}},
        row{{1-Z}} = {{font={self.font_size}}},
        row{{1}} = {{bg={self.header_color}, font={self.font_size}\bfseries}},
        hlines,
        rowhead={{1}},
        vlines,
        width={self.width}
        }}
        {headers}
        {body}
        \end{{longtblr}}
        """.strip()
