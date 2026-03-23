import pandas as pd
import re
import unicodedata

from pathlib import Path

from deasy_puce import Informe

class Horario(Informe):
    def __init__(self, periodo, exel_path=None, input_paths=None):
        self.__titulo='HORARIO DE CLASES'
        super().__init__(periodo, self.__titulo)
        self.data_path=None
        self._set_input_path(exel_path=exel_path, input_paths=input_paths)
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
        
    def __set_output_group(self, group):
        base_dir = Path(self._save_path)
        self._tables_dir = base_dir / "tables" / group
        self._tables_dir.mkdir(parents=True, exist_ok=True)
        self._content_file = base_dir / f"Content_{group}.tex"
        self._clean_latex_files()

    def _set_input_path(self, exel_path=None, input_paths=None):
        if input_paths is not None:
            if not isinstance(input_paths, dict):
                raise TypeError("input_paths debe ser un dict con clave 'horario'.")
            exel_path = input_paths.get("horario", exel_path)

        selected = exel_path or f"./assets/Horarios/Horario{self._periodo['actual']}.xlsx"
        self.data_path = Path(selected)

    def __safe_slug(self, value):
        value = str(value).strip()
        value = re.sub(r"\s+", "_", value)
        value = re.sub(r"[\\/:\*\?\"<>\|]+", "-", value)
        return value

    def load_data(self, exel_path=None, input_paths=None):
        if exel_path is not None or input_paths is not None:
            self._set_input_path(exel_path=exel_path, input_paths=input_paths)
        try:
            self.dataframe = self.__read_horario_excel()
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

    def __read_horario_excel(self):
        expected = [
            "CARRERA",
            "APELLIDOS Y NOMBRES",
            "CURSO",
            "CODIGO",
            "MATERIA",
            "MATERIA.1",
            "CURSO.1",
            "NRC",
            "DIA",
            "HORARIO",
            "Nº CREDITOS",
            "T. CRED.",
            "INIC. Y FIN SEM.",
            "OBSERVACIONES",
            "AULA",
        ]

        def _canon_header(text):
            text = str(text).replace("\u00A0", " ").strip().upper()
            text = unicodedata.normalize("NFKD", text)
            text = "".join(ch for ch in text if not unicodedata.combining(ch))
            text = re.sub(r"[\s\.\-_/]+", "", text)
            text = re.sub(r"[^A-Z0-9]+", "", text)
            return text

        expected_canon = {_canon_header(x) for x in expected}

        df_default = pd.read_excel(self.data_path)
        cols_default = {_canon_header(c) for c in df_default.columns}
        if cols_default & expected_canon:
            return df_default

        df_raw = pd.read_excel(self.data_path, header=None)
        best_row = None
        best_score = 0

        max_rows = min(25, len(df_raw))
        for i in range(max_rows):
            row_vals = {_canon_header(v) for v in df_raw.iloc[i].tolist()}
            score = len(row_vals & expected_canon)
            if score > best_score:
                best_score = score
                best_row = i

        if best_row is None or best_score < 4:
            return df_default

        headers = df_raw.iloc[best_row].tolist()
        data = df_raw.iloc[best_row + 1 :].copy()
        data.columns = headers
        data = data.dropna(how="all").reset_index(drop=True)
        return data

    def __rename_columnas(self):
        self.dataframe.columns = self.dataframe.columns.astype(str).str.strip()

        columnas_requeridas_map = {
            'CARRERA': 'Carrera',
            'APELLIDOS Y NOMBRES': 'Docente',
            'CURSO': 'Nivel',
            'MATERIA': 'Asignatura', 
            'NRC': 'NRC',
            'DIA': 'Día',
            'HORARIO': 'Horario',
            'AULA':'Aula'
        }
        columnas_opcionales_map = {
            'CODIGO': 'Código',
            'MATERIA.1': 'Materia',
            'CURSO.1': 'Curso',
            'Nº CREDITOS': 'Créditos',
            'T. CRED.': 'T. Créditos',
            'INIC. Y FIN SEM.': 'Periodo',
            'OBSERVACIONES': 'Observaciones',
        }
        columnas_map = {**columnas_requeridas_map, **columnas_opcionales_map}

        def _canon_header(text):
            text = str(text).replace("\u00A0", " ").strip().upper()
            text = unicodedata.normalize("NFKD", text)
            text = "".join(ch for ch in text if not unicodedata.combining(ch))
            text = re.sub(r"[\s\.\-_/]+", "", text)
            text = re.sub(r"[^A-Z0-9]+", "", text)
            return text

        columnas_map_canon = {_canon_header(k): v for k, v in columnas_map.items()}
        columnas_requeridas_canon = {_canon_header(k): v for k, v in columnas_requeridas_map.items()}
        cols_detectadas_canon = {_canon_header(c): c for c in self.dataframe.columns}

        faltantes = sorted(set(columnas_requeridas_canon) - set(cols_detectadas_canon))
        if faltantes:
            faltantes_legibles = [k for k in columnas_requeridas_map if _canon_header(k) in set(faltantes)]
            raise ValueError(
                "El Archivo Excel no cumple el formato esperado.\n"
                "Debe contener al menos estas columnas requeridas:\n"
                + "\n".join(f"- {c}" for c in sorted(columnas_requeridas_map))
                + "\n\nFaltan:\n"
                + "\n".join(f"- {c}" for c in sorted(faltantes_legibles))
            )

        rename_dict = {}
        for canon, col_real in cols_detectadas_canon.items():
            if canon in columnas_map_canon:
                rename_dict[col_real] = columnas_map_canon[canon]

        self.dataframe = self.dataframe.rename(columns=rename_dict)

        # Para tablas/NRCs se usa siempre el nombre de asignatura textual (MATERIA).
        if "Asignatura" in self.dataframe.columns:
            self.dataframe["Materia"] = self.dataframe["Asignatura"]

    
    def prepare_data(self):
        #self.__ordenar_dataframe() ## Inncesario de momento
        self.__expadir_nrcs()
        self.__normalizar_data()
        

    def __expadir_nrcs(self):
        # Rellenar NRCs faltantes sin mezclar niveles/paralelos distintos.
        group_cols = ["Materia"]
        if "Nivel" in self.dataframe.columns:
            group_cols.append("Nivel")
        if "Curso" in self.dataframe.columns:
            group_cols.append("Curso")

        self.dataframe["NRC"] = pd.to_numeric(self.dataframe["NRC"], errors="coerce")
        self.dataframe = self.dataframe.sort_values(group_cols + ["NRC"], na_position="last")
        self.dataframe["NRC"] = self.dataframe.groupby(group_cols)["NRC"].transform(
            lambda x: x.ffill().bfill()
        )
        self.dataframe["NRC"] = self.dataframe["NRC"].astype("Int64")
        

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
        self.dataframe["Día"] = self.dataframe["Día"].apply(self.__normalizar_dia)
        self.dataframe["Nivel"] = self.dataframe["Nivel"].apply(self.__normalizar_nivel)
        self.dataframe["Horario"] = self.__normalizar_horario(self.dataframe["Horario"])


    def __normalizar_dia(self, value):
        if pd.isna(value):
            return value
        if not isinstance(value, str):
            value = str(value)
        value = " ".join(value.split())
        return self.text_title_case(value)

    def __normalizar_nivel(self, value):
        if pd.isna(value):
            return value
        if not isinstance(value, str):
            value = str(value)
        value = " ".join(value.split())
        if value == "":
            return value

        value = self.text_title_case(value)
        canon = unicodedata.normalize("NFKD", value)
        canon = "".join(ch for ch in canon if not unicodedata.combining(ch))
        canon = re.sub(r"[^a-zA-Z0-9]+", "", canon).lower()

        nivel_map = {
            "1": "Primero", "primero": "Primero",
            "2": "Segundo", "segundo": "Segundo",
            "3": "Tercero", "tercero": "Tercero",
            "4": "Cuarto", "cuarto": "Cuarto",
            "5": "Quinto", "quinto": "Quinto",
            "6": "Sexto", "sexto": "Sexto",
            "7": "Séptimo", "septimo": "Séptimo",
            "8": "Octavo", "octavo": "Octavo",
        }
        return nivel_map.get(canon, value)
    

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
            mat.columns = pd.Index([self.__normalizar_dia(d) for d in mat.columns])

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
        for nivel, grupo in self.df_horarios.groupby(by, dropna=True):
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
            self.__set_output_group("niveles")
            
            for carrera in carreras:
                self.df_horarios=self.dataframe[self.dataframe['Carrera']==carrera]
                niveles_extra = sorted(
                    set(self.df_horarios["Nivel"].dropna().unique()) - set(self.__orden_nivel)
                )
                categorias_nivel = self.__orden_nivel + niveles_extra
                self.df_horarios["Nivel"]=pd.Categorical(
                    self.df_horarios["Nivel"], categories=categorias_nivel, ordered=True
                )
                self.df_horarios=self.df_horarios.sort_values('Nivel')
                self.__build_horarios_latex('Nivel', carrera, output_group="niveles")

    def get_horarios_por_docente(self):
        self.__set_output_group("docentes")
        self.df_horarios=self.dataframe
        self.df_horarios=self.df_horarios.dropna(subset=['Docente']).sort_values('Docente')
        self.__build_horarios_latex('Docente', output_group="docentes")

    def get_nrcs_unicos(self):
        if not hasattr(self, "dataframe"):
            raise RuntimeError("Ejecuta load_data() y prepare_data() antes de pedir NRCs únicos.")
        if "NRC" not in self.dataframe.columns:
            raise ValueError("No se encontró la columna NRC en los datos de horario.")

        nrc_values = self.dataframe["NRC"].astype(str).str.strip().str.lower()
        tiene_nrcs = nrc_values[~nrc_values.isin({"", "nan", "none", "0", "0.0"})]
        if tiene_nrcs.empty:
            raise ValueError("No se encontraron NRCs.")

        carreras = self.dataframe["Carrera"].dropna().unique()
        self.__set_output_group("nrcs")

        for carrera in carreras:
            df_carrera = self.dataframe[self.dataframe["Carrera"] == carrera].copy()
            df_carrera["Nivel"] = (
                df_carrera["Nivel"]
                .astype(str)
                .str.strip()
                .replace({"": "Sin Nivel", "nan": "Sin Nivel", "None": "Sin Nivel"})
            )
            niveles_extra = sorted(
                set(df_carrera["Nivel"].unique()) - set(self.__orden_nivel) - {"Sin Nivel"}
            )
            orden_niveles = self.__orden_nivel + niveles_extra + ["Sin Nivel"]
            df_carrera["Nivel"] = pd.Categorical(
                df_carrera["Nivel"],
                categories=orden_niveles,
                ordered=True
            )
            df_carrera = df_carrera.sort_values("Nivel")
            self.__build_nrcs_unicos_latex(df_carrera, carrera, output_group="nrcs")


    def __build_horarios_latex(self, by="Nivel", carrera='General', output_group="niveles"):
        
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
                carrera_name = self.__safe_slug(carrera)
                key_name = self.__safe_slug(key)
                file_name = f"{carrera_name}_{key_name}.tex"
                table_file = self._tables_dir / file_name
                with open(table_file, "w", encoding="utf-8") as f:
                    f.write(table)

                content+=header+"\\input{Contenido/tables/"+output_group+"/"+file_name+"}\n \\newpage\n"
            
        with open(self._content_file,"a", encoding="utf-8") as f:
                f.write(content)

    def __build_nrcs_unicos_latex(self, df_carrera, carrera, output_group="nrcs"):
        print("Building NRC tables... for"+carrera)

        content = ""
        for nivel, grupo in df_carrera.groupby("Nivel", dropna=True):
            df_table = (
                grupo[["Materia", "NRC", "Docente", "Aula"]]
                .dropna(subset=["Materia", "NRC"], how="any")
                .drop_duplicates()
                .sort_values(["Materia", "NRC", "Docente", "Aula"])
                .reset_index(drop=True)
            )

            if df_table.empty:
                continue

            header = f"""
            \\begin{{center}}
            \\Large\\titulo\\\\ 
            \\large SEMESTRE: {self._months_period}
            \\end{{center}}
            \\noindent
            \\large
            \\begin{{tblr}}{{colspec = {{Q[l,m,2cm] Q[l,m,15.7cm] Q[r,m,5.7cm]}}, rows = {{m}},}}
            \\textbf{{Carrera:}} & {carrera} & \\textbf{{ Nivel:}} {nivel} \\
            \\end{{tblr}}
            """

            col_scale = [8, 2, 6, 3]
            col_halign = ["l", "c", "l", "c"]
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

            carrera_name = self.__safe_slug(carrera)
            nivel_nombre = self.__safe_slug(nivel)
            table_name = f"{carrera_name}_nrcs_{nivel_nombre}.tex"
            table_file = self._tables_dir / table_name
            with open(table_file, "w", encoding="utf-8") as f:
                f.write(table)

            content += header + "\\input{Contenido/tables/" + output_group + "/" + table_name + "}\n \\newpage\n"

        with open(self._content_file, "a", encoding="utf-8") as f:
            f.write(content)
        
