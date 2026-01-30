import pandas as pd

from pathlib import Path

from deasy_puce import Informe

class Horario(Informe):
    def __init__(self, periodo, exel_path=None):
        self.__titulo='HORARIO DE CLASES'
        super().__init__(periodo, self.__titulo)
        self.data_path=exel_path or f'./assets/Horarios/Horario{periodo}.xlsx'
        self._semestre=self._months_period
        self.__orden_dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        self.__orden_nivel=["Primero", "Segundo", "Tercero", "Cuarto", "Quinto", "Sexto", "Séptimo", "Octavo"]
        self.__orden_horas = [
            "07:00-08:00","08:00-09:00","09:00-10:00",
            "10:00-11:00","11:00-12:00","12:00-13:00",
            "13:00-14:00","14:00-15:00","15:00-16:00",
            "16:00-17:00","17:00-18:00","18:00-19:00",
            "19:00-20:00","20:00-21:00","21:00-22:00",
        ]
        

    def load_data(self):
        try:
            self.dataframe = pd.read_excel(self.data_path)
            self.dataframe = self.df_title_case(self.dataframe)

            self.__rename_columnas()

        except FileNotFoundError:
            raise FileNotFoundError(
                f"No se encontró el archivo de horario: {self.data_path}\n"
                "Asegúrese de ejecutar el comando desde el directorio correcto y que el archivo exista."
            )
        except ValueError as e:
            # Error de “formato de entrada” (mensaje para el usuario)
            raise ValueError(
                f"Formato inválido del archivo de horario: {self.data_path}\n{e}"
            )
        except Exception as e:
            raise RuntimeError(
                f"No se pudo cargar/procesar el horario desde: {self.data_path}\n"
                f"Detalle: {e}"
            )

    def __rename_columnas(self):
        self.dataframe.columns = self.dataframe.columns.str.strip()

        columnas_map = {
            'CARRERA': 'Carrera',
            'APELLIDOS Y NOMBRES': 'Docente',
            'CURSO': 'Nivel',
            'CODIGO': 'Código', #Posible borrado
            'MATERIA': 'Asignatura', 
            'MATERIA.1': 'Materia', #Posible borrado
            'CURSO.1': 'Curso', #Posible borrado
            'NRC': 'NRC',
            'DIA': 'Día',
            'HORARIO': 'Horario',
            'Nº CREDITOS': 'Créditos', #Posible borrado
            'T. CRED.': 'T. Créditos', #Posible borrado
            'INIC. Y FIN SEM.': 'Periodo', #Posible borrado
            'OBSERVACIONES': 'Observaciones', #Posible borrado
            'AULA':'Aula'
        }

        faltantes = set(columnas_map) - set(self.dataframe.columns)
        if faltantes:
            raise ValueError(
                "El Archivo Excel no cumple el formato esperado.\n"
                "Debe contener al menos estas columnas:\n"
                + "\n".join(f"- {c}" for c in sorted(columnas_map))
                + "\n\nFaltan:\n"
                + "\n".join(f"- {c}" for c in sorted(faltantes))
            )

        self.dataframe = self.dataframe.rename(columns=columnas_map)

    
    def prepare_data(self):
        #self.__ordenar_dataframe() ## Inncesario de momento
        self.__expadir_nrcs()
        self.__normalizar_data()
        

    def __expadir_nrcs(self):
        #self.dataframe=self.dataframe.copy()
        self.dataframe=self.dataframe.sort_values(['Materia','NRC'])
        self.dataframe["NRC"] = self.dataframe.groupby("Materia")["NRC"].transform(lambda x: x.ffill().bfill())
        self.dataframe["NRC"] = self.dataframe["NRC"].fillna(0)
        self.dataframe["NRC"] = self.dataframe["NRC"].astype(int)
        

    def __normalizar_horario(self, col):
        return (
            col.astype(str)
            .str.strip()
            # normalizar distintos tipos de guiones a "-"
            .str.replace(r"[–—−]+", "-", regex=True)
            # eliminar espacios alrededor del guion
            .str.replace(r"\s*-\s*", "-", regex=True)
            # eliminar segundos si vienen (07:00:00 → 07:00)
            .str.replace(r":00(?=:)", "", regex=True)
            # asegurar formato HH:MM-HH:MM
            .str.extract(r"(\d{2}:\d{2}-\d{2}:\d{2})", expand=False)
        )


    def __normalizar_data(self):

        self.dataframe["Aula"]=self.dataframe["Aula"].fillna('')
        extraido = self.dataframe["Aula"].str.extract(r"(AULA\s*\d+)", expand=False)
        self.dataframe["Aula"] = extraido.fillna(self.dataframe["Aula"]).str.strip()
        self.dataframe["Aula"] = self.dataframe["Aula"].str.replace(r"(?i)(AULA)(\d+)", r"\1 \2", regex=True)
        self.dataframe["Aula"] = self.dataframe["Aula"].str.replace(r"\s+", " ", regex=True).str.strip()
        self.dataframe["Día"] = self.dataframe["Día"].astype(str).str.strip()#.str.upper()
        self.dataframe["Horario"] = self.__normalizar_horario(self.dataframe["Horario"])


    

    def _texto_evento(self, r, by='Nivel'):
        # Puedes ajustar el formato según lo que necesites
        aula = r.get("Aula", "")
        nrc = r.get("NRC", "")
        materia = r.get("Asignatura", "")
        pivote = {
          "Docente": f"{r.get('Nivel', '')}: {r.get('Carrera', '')}",
          "Nivel": str(r.get("Docente", ""))
        }
        resultado=f"{{ {materia}\\\\NRC: {nrc}\\\\{ pivote.get(by, '')}\\\\{aula} }}".strip()
        return resultado

    


    def __get_values_off(self, mat):

            horas_fuera = sorted(set(mat.index) - set(self.__orden_horas))
            if horas_fuera:
                raise ValueError(
                    "Se encontraron horas no contempladas en el catálogo oficial.\n"
                    "Horas detectadas:\n"
                    + "\n".join(f"- {h}" for h in horas_fuera)
                    + "\n\nHoras permitidas:\n"
                    + "\n".join(f"- {h}" for h in self.__orden_horas)
                )
            
            dias_fuera = sorted(set(mat.columns) - set(self.__orden_dias))
            if dias_fuera:
                raise ValueError(
                    "Se encontraron días no contemplados en el catálogo oficial.\n"
                    "Días detectados:\n"
                    + "\n".join(f"- {d}" for d in dias_fuera)
                    + "\n\nDías permitidos:\n"
                    + "\n".join(f"- {d}" for d in self.__orden_dias)
                )

    def __get_horarios(self, by="Nivel"):
        """
        Devuelve un dict: {nivel: dataframe_horario}
        Cada dataframe tiene index = horas, columns = días.
        """
        out = {}
        for nivel, grupo in self.df_horarios.groupby(by, dropna=False):
            grupo = grupo.copy()

            # Creamos una columna "Evento" (texto que va dentro de la celda)
            grupo["Evento"] = grupo.apply(lambda r: self._texto_evento(r, by), axis=1)

            # Si hay múltiples eventos en la misma celda (mismo día/hora),
            # los unimos con doble salto de línea.
            agg = (grupo.groupby(["Horario", "Día"])["Evento"]
                     .apply(lambda s: "\n\n".join(s.astype(str)))
                     .reset_index())
            
            # Pivot: filas=Horario, columnas=Día, valores=Evento
            mat = agg.pivot(index="Horario", columns="Día", values="Evento")

            self.__get_values_off(mat)

            mat.index = pd.CategoricalIndex(
                mat.index,
                categories=self.__orden_horas,
                ordered=True
            )

            mat = mat.sort_index()

            mat.columns = pd.CategoricalIndex(
                mat.columns,
                categories=self.__orden_dias,
                ordered=True
            )

            mat = mat.sort_index(axis=1)

            mat = mat.fillna("")
            out[nivel] = mat

        return out

    def get_horarios_por_nivel(self):
            carreras=self.dataframe['Carrera'].unique()
            self._clean_latex_files()
            
            for carrera in carreras:
                self.df_horarios=self.dataframe[self.dataframe['Carrera']==carrera]
                self.df_horarios["Nivel"]=pd.Categorical(self.df_horarios["Nivel"], categories=self.__orden_nivel, ordered=True)
                self.df_horarios=self.df_horarios.sort_values('Nivel')
                self.__build_horarios_latex('Nivel', carrera)

    def get_horarios_por_docente(self):
        self._clean_latex_files()
        self.df_horarios=self.dataframe
        self.df_horarios=self.df_horarios.sort_values('Docente')
        self.__build_horarios_latex('Docente')


    def __build_horarios_latex(self, by="Nivel", carrera='General'):
        
        print("Building tables... for"+carrera)
        
        horarios=self.__get_horarios(by)
        content=''
        for key in horarios:
            header=f"""
            \\begin{{center}}
            \\Large\\titulo\\\\ 
            \\large SEMESTRE: {self._months_period}
            \\end{{center}}
            \\noindent
            \\large
            \\begin{{tblr}}{{colspec = {{Q[l,m,2cm] Q[l,m,15.7cm] Q[r,m,5.7cm]}}, rows = {{m}},}}
            \\textbf{{Carrera:}} & {carrera} & \\textbf{{ {by}:}} {key} \\
            \\end{{tblr}}
            """
            df_table=horarios[key].reset_index()           
            col_scale=[2]*len(df_table.columns)
            col_scale[0]=1
            col_halign=['c']*len(df_table.columns)

            table = self.dataframe_to_latex(
                df_table,
                caption='',
                label='',
                set_caption='empty',
                h_align=col_halign,
                scale=col_scale,
                options='', 
                props="row{odd} = {bg=colhead!10}"
            )

            if table!="":
                table_file = self._tables_dir / f"{carrera.replace(' ', '_')}_{key}.tex"
                with open(table_file, "w", encoding="utf-8") as f:
                    f.write(table)

                content+=header+"\\input{Contenido/tables/"+carrera.replace(' ', '_')+f"_{key}.tex"+"}\n \\newpage\n"
            
        with open(self._content_file,"a", encoding="utf-8") as f:
                f.write(content)
        