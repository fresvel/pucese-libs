import pandas as pd
from jinja2 import Template
from pathlib import Path

from deasy_puce.latex.tblr import LatexTblr

class Informe():

    _CICLOS_I = {61, 12}
    _CICLOS_II = {66, 16}

    def __init__(self, periodo, titulo="TITULO", base=2):
        self.__periodo=periodo
        self.__titulo=titulo
        self.__anio=int(periodo[:4])
        self.__ciclo=int(periodo[4:])
        self.__base=base
        self.obtener_periodos()
        self.__set_beauty_period()
        self.version="Informe 0.1.6"
        self.template_header="../Latex/Contenido/Header.tex.j2"
        self.output_header="../Latex/Contenido/Header.tex"

    def __set_beauty_period(self):
        if self.__ciclo in self._CICLOS_I:
            sufijo = "-I"
        elif self.__ciclo in self._CICLOS_II:
            sufijo = "-II"
        else:
            raise ValueError(f"Ciclo inválido: {self.__ciclo}")

        self.__beauty_period = f"{self.__anio}{sufijo}"
    
    def obtener_periodos(self):
        keep_anio_previo=["66","16"]
        map_ciclo_previo={
            "61":66,
            "12":16,
            "66":61,
            "16":12}
        self._periodo={
                "actual":self.__periodo,
                "previo":str(self.__anio)+map_ciclo_previo[str(self.__ciclo)] if self.__ciclo in keep_anio_previo else str(self.__anio-1)+str(map_ciclo_previo[str(self.__ciclo)]),
                "base":str(self.__anio-self.__base)+str(self.__ciclo)
                }

    def text_title_case(self, text):
        if pd.isna(text):
            return text
        
        if not isinstance(text, str):
            return text

        text = text.lower().title()
        excepciones = {"De", "Y", "En", "La", "El", "Del", "Con", "Para", "A"}
        palabras = text.split()
        resultado = [palabra if palabra not in excepciones else palabra.lower()
                     for palabra in palabras]
        text = " ".join(resultado)
        excepciones = {"Ii", "Iii", "Vi"}
        palabras = text.split()
        resultado = [palabra if palabra not in excepciones else palabra.upper()
                     for palabra in palabras]
        return " ".join(resultado)


    def df_title_case(self, df):
        df = df.copy()
        for col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].apply(self.text_title_case)
        return df
    
    
    def dataframe_to_latex(self,df,caption,label,h_align=None,v_align=None,scale=None,**kwargs):
        builder = LatexTblr(**kwargs)
        return builder.from_dataframe(
            df,
            caption,
            label,
            h_align=h_align,
            v_align=v_align,
            scale=scale
        )
    
    def render_header_tex(self, carrera):
        template_text = Path(self.template_header).read_text(encoding="utf-8")
        template = Template(template_text)

        rendered = template.render(
            carrera=carrera,
            periodo=self.__beauty_period,
            titulo=self.__titulo
        )
        Path(self.output_header).write_text(rendered, encoding="utf-8")

