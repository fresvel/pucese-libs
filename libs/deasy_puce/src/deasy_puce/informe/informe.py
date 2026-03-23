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
        self._anio=int(periodo[:4])
        self.__ciclo=int(periodo[4:])
        self.__base=base
        self._roman_period, self._months_period, self._letter_period, self._number_period='','','',''
        self.obtener_periodos()
        self.__set_names_period()
        self.version="Informe 0.1.11"
        self.template_header="../Latex/Contenido/Header.tex.j2"
        self.output_header="../Latex/Contenido/Header.tex"
        content_dir = self._get_writable_content_dir()
        self._save_path = str(content_dir) + "/"
        self._tables_dir = content_dir / "tables"
        self._tables_dir.mkdir(parents=True, exist_ok=True)
        self._content_file = content_dir / "Content.tex"

    def _get_writable_content_dir(self):
        candidates = [
            Path("../Latex/Contenido/"),
            Path.cwd() / "Latex" / "Contenido",
        ]

        last_error = None
        for candidate in candidates:
            try:
                (candidate / "tables").mkdir(parents=True, exist_ok=True)
                return candidate
            except OSError as exc:
                last_error = exc

        if last_error is not None:
            raise last_error
        raise OSError("No se pudo inicializar un directorio de salida para los informes.")

    def __set_names_period(self):
        if self.__ciclo in self._CICLOS_I:
            sufijo = "-I"
            self._ciclo=1
            self._months_period = f"ABRIL {self._anio} - AGOSTO {self._anio}"
        elif self.__ciclo in self._CICLOS_II:
            sufijo = "-II"
            self._ciclo=2
            self._months_period = f"OCTUBRE {self._anio} - FEBRERO {self._anio+1}"
        else:
            raise ValueError(f"Ciclo inválido: {self.__ciclo}")

        self._roman_period = f"{self._anio}{sufijo}"
        self._letter_period = f"{self._anio}S{self._ciclo}"
        self._number_period = f"{self._anio}-0{self._ciclo}"


        
    
    def obtener_periodos(self):
        keep_anio_previo=["66","16"]
        map_ciclo_previo={
            "61":66,
            "12":16,
            "66":61,
            "16":12}
        self._periodo={
                "actual":self.__periodo,
                "previo":str(self._anio)+map_ciclo_previo[str(self.__ciclo)] if self.__ciclo in keep_anio_previo else str(self._anio-1)+str(map_ciclo_previo[str(self.__ciclo)]),
                "base":str(self._anio-self.__base)+str(self.__ciclo)
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
            if pd.api.types.is_string_dtype(df[col]) or df[col].dtype == "object":
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
            periodo=self._roman_period,
            titulo=self.__titulo
        )
        Path(self.output_header).write_text(rendered, encoding="utf-8")


    def _clean_latex_files(self):
        for file in self._tables_dir.glob("*.tex"):
                file.unlink()

        with open(self._content_file,"w", encoding="utf-8") as f:
                f.write('')
