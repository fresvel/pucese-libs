import pandas as pd
from deasy_puce.latex.tblr import LatexTblr

class Informe():
    def __init__(self, periodo, base=2):
        self.__periodo=periodo
        self.__anio=int(periodo[:4])
        self.__ciclo=int(periodo[4:])
        self.__base=base
        self.obtener_periodos()
        self.version="Informe 0.1.5"
        

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

