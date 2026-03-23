import pandas as pd
import matplotlib.pyplot as plt

try:
    import seaborn as sns
except Exception:  # pragma: no cover - optional
    sns = None

try:
    from IPython.display import display
except Exception:  # pragma: no cover - optional in notebooks
    def display(_obj):
        return None

from pathlib import Path
from deasy_puce import Informe


class InformeDesercion(Informe):
    TITULO = "Informe de Deserción Estudiantil"
    ESTADO_ACTIVO = "Activo"
    ESTADO_DESERCION = "Deserción"
    ESTADO_INACTIVO = "Inactivo"
    ESTADO_GRADUADO = "Graduado"
    ESTADO_REINGRESO = "Reingreso"
    ESTADO_ANTIGUO = "Antiguo"
    ESTADO_NUEVO = "Nuevo"
    DENOMINACION_NUEVO = "NUEVO"
    CAPTION_LISTADO = "Listado de estudiantes identificados en deserción, inactividad o reingreso"
    LABEL_LISTADO = "listado_estudiantes"
    LISTADO_COLUMNS = ["N°", "Estudiante", "Estado", "Nivel", "Media", "Éxito", "Contacto", "Observación"]
    LISTADO_EMPTY_ROW = [1, "No se encontraron datos.", "", "", "", "", "", ""]
    GRADE_STATUS_VALIDOS = ["APROBADO", "REPROBADO"]
    GRADE_STATUS_APROBADO = "APROBADO"
    GRADE_STATUS_REPROBADO = "REPROBADO"
    GRADE_TYPE_CUANTITATIVO = "cuantitativo"
    GRADE_TYPE_CUALITATIVO = "cualitativo"
    DEFAULT_GRADE_CONVERSION = {"A": 50, "B": 45, "C": 35, "D": 29}

    def __init__(
        self,
        periodo,
        programa,
        inscritos_path,
        egresados_path,
        grades_path,
        sep=";",
        image_path="../Latex/Contenido/Images/",
        grade_conversion=None,
    ):
        super().__init__(periodo, titulo=self.TITULO)

        self.__programa = programa
        self.__sep = sep
        self._image_path = Path(image_path)
        self._image_path.mkdir(parents=True, exist_ok=True)
        self.__periodos = self._build_periodos(periodo)

        self.__paths = {
            "inscritos": inscritos_path,
            "egresados": egresados_path,
            "grades": grades_path,
        }
        self._grade_conversion = dict(grade_conversion or self.DEFAULT_GRADE_CONVERSION)
        self._grade_file_type = None

        self.__columnas = [
            "ID_BANNER",
            "APELIDOS",
            "PRIMER_NOMBRE",
            "SEGUNDO_NOMBRE",
            "CEDULA",
            "PERIODO",
            "DENOMINACION_A_N",
            "NIVEL_POR_MATERIAS",
            "CELULAR",
        ]

        self.__df_inscritos = None
        self.__df_referencia = None
        self.__df_actuales = None
        self.__df_previos = None
        self.__df_egresados = None
        self.__df_grades = None

        self.__df_nuevos = None
        self.__df_desertores = None
        self.__df_inactivos = None
        self.__df_graduados = None
        self.__df_reingreso = None
        self.__df_informe = None

        self.__tasa_desercion = None
        self.__conteos = None

    def _format_table_value(self, value, decimals=None):
        if pd.isna(value) or value == "":
            return "-"
        if decimals is not None:
            try:
                return f"{float(value):.{decimals}f}"
            except (TypeError, ValueError):
                return str(value)
        return str(value)

    def _format_phone(self, value):
        if pd.isna(value) or value == "":
            return "-"
        try:
            number = str(value).strip()
            if number.endswith(".0"):
                number = number[:-2]
            return number or "-"
        except Exception:
            return "-"

    def _build_listado_dataframe(self):
        if self.__df_informe is None:
            raise RuntimeError("Ejecuta load_data() y prepare_data() antes de pedir los dataframes.")

        if self.__df_informe.empty:
            return pd.DataFrame(
                [self.LISTADO_EMPTY_ROW],
                columns=self.LISTADO_COLUMNS,
            )

        df_table = self.__df_informe.copy()
        if "mean" not in df_table.columns:
            df_table["mean"] = pd.NA
        if "exito" not in df_table.columns:
            df_table["exito"] = pd.NA
        if "CELULAR" not in df_table.columns:
            df_table["CELULAR"] = pd.NA

        df_table = df_table.assign(
            **{
                "N°": range(1, len(df_table) + 1),
                "Estudiante": df_table["Nombre"].fillna("-"),
                "Estado": df_table["ESTADO"].fillna("-"),
                "Nivel": df_table["NIVEL_POR_MATERIAS"].apply(self._format_table_value),
                "Media": df_table["mean"].apply(lambda value: self._format_table_value(value, decimals=2)),
                "Éxito": df_table["exito"].apply(lambda value: self._format_table_value(value, decimals=2)),
                "Contacto": df_table["CELULAR"].apply(self._format_phone),
                "Observación": "",
            }
        )

        return df_table[self.LISTADO_COLUMNS]

    def _build_grades_metrics(self):
        if "id_banner_estudiante" not in self.__df_grades.columns:
            return pd.DataFrame(columns=["id_banner_estudiante", "mean", "exito"])

        df_grades_src = self._prepare_grades_dataframe()

        if "estado" in df_grades_src.columns:
            df_grades_src["estado"] = df_grades_src["estado"].astype("string").str.strip().str.upper()
        else:
            df_grades_src["estado"] = pd.Series(pd.NA, index=df_grades_src.index, dtype="string")

        df_means = (
            df_grades_src.dropna(subset=["nota_final"])
            .groupby("id_banner_estudiante")["nota_final"]
            .mean()
            .round(2)
            .reset_index(name="mean")
        )

        df_estado = df_grades_src[df_grades_src["estado"].isin(self.GRADE_STATUS_VALIDOS)].copy()
        if df_estado.empty:
            df_exito = pd.DataFrame(columns=["id_banner_estudiante", "exito"])
        else:
            aprobado = df_estado.groupby("id_banner_estudiante")["estado"].apply(
                lambda x: (x == self.GRADE_STATUS_APROBADO).sum()
            )
            reprobado = df_estado.groupby("id_banner_estudiante")["estado"].apply(
                lambda x: (x == self.GRADE_STATUS_REPROBADO).sum()
            )
            total = aprobado + reprobado
            df_exito = ((100 * aprobado) / total.where(total != 0)).round(2).reset_index(name="exito")

        return pd.merge(df_means, df_exito, on="id_banner_estudiante", how="outer")

    def _detect_grades_file_type(self, df):
        if "nota_final" not in df.columns:
            return self.GRADE_TYPE_CUANTITATIVO

        notas = df["nota_final"].dropna().astype(str).str.strip().str.upper()
        notas = notas[notas != ""]
        if notas.empty:
            return self.GRADE_TYPE_CUANTITATIVO

        notas_numericas = pd.to_numeric(notas, errors="coerce")
        if notas_numericas.notna().all():
            return self.GRADE_TYPE_CUANTITATIVO

        notas_validas = set(notas.unique())
        if notas_validas.issubset(set(self._grade_conversion.keys())):
            return self.GRADE_TYPE_CUALITATIVO

        return self.GRADE_TYPE_CUANTITATIVO

    def _deduplicate_grades(self, df):
        df = df.copy()
        if "nota_final" in df.columns:
            nota_clean = df["nota_final"].astype("string").str.strip()
        else:
            nota_clean = pd.Series("", index=df.index, dtype="string")

        if "estado" in df.columns:
            estado_clean = df["estado"].astype("string").str.strip()
        else:
            estado_clean = pd.Series("", index=df.index, dtype="string")

        df["_has_grade"] = nota_clean.fillna("").ne("")
        df["_has_estado"] = estado_clean.fillna("").ne("")

        dedup_cols = ["id_banner_estudiante"]
        if "codigo_periodo" in df.columns:
            dedup_cols.append("codigo_periodo")
        if "titulo_curso" in df.columns:
            dedup_cols.append("titulo_curso")

        if len(dedup_cols) > 1:
            df = df.sort_values(["_has_grade", "_has_estado"], ascending=[False, False])
            df = df.drop_duplicates(subset=dedup_cols, keep="first")

        return df.drop(columns=["_has_grade", "_has_estado"], errors="ignore")

    def _prepare_grades_dataframe(self):
        df_grades_src = self.__df_grades.copy()
        self._grade_file_type = self._detect_grades_file_type(df_grades_src)

        if self._grade_file_type == self.GRADE_TYPE_CUALITATIVO:
            df_grades_src = self._deduplicate_grades(df_grades_src)
            if "nota_final" in df_grades_src.columns:
                notas = df_grades_src["nota_final"].astype("string").str.strip().str.upper()
                df_grades_src["nota_final"] = notas.map(self._grade_conversion)
        else:
            df_grades_src["nota_final"] = pd.to_numeric(df_grades_src.get("nota_final"), errors="coerce")

        df_grades_src["nota_final"] = pd.to_numeric(df_grades_src.get("nota_final"), errors="coerce")
        return df_grades_src

    def _build_nombre_series(self, df):
        nombres = (
            df["APELIDOS"].fillna("").astype(str).str.strip()
            + " "
            + df["PRIMER_NOMBRE"].fillna("").astype(str).str.strip()
            + " "
            + df["SEGUNDO_NOMBRE"].fillna("").astype(str).str.strip()
        )
        nombres = nombres.str.replace(r"\s+", " ", regex=True).str.strip()
        nombres = nombres.mask(nombres == "", df["ID_BANNER"].astype(str))
        return nombres.apply(self.text_title_case)

    def _prepare_desertores(self):
        self.__df_referencia = self.__df_referencia[
            self.__df_referencia["DENOMINACION_A_N"] == self.DENOMINACION_NUEVO
        ].reset_index(drop=True)
        self.__df_referencia["ESTADO"] = self.__df_referencia["ID_BANNER"].isin(self.__df_actuales["ID_BANNER"]).map(
            {True: self.ESTADO_ACTIVO, False: self.ESTADO_DESERCION}
        )
        self.__df_desertores = self.__df_referencia[
            self.__df_referencia["ESTADO"] == self.ESTADO_DESERCION
        ].reset_index(drop=True)

        base = self.__df_referencia["ID_BANNER"].count()
        self.__tasa_desercion = (self.__df_desertores["ID_BANNER"].size / base) if base else 0

    def _prepare_inactivos(self):
        self.__df_previos["ESTADO"] = self.__df_previos["ID_BANNER"].isin(self.__df_actuales["ID_BANNER"]).map(
            {True: self.ESTADO_ACTIVO, False: self.ESTADO_INACTIVO}
        )
        self.__df_inactivos = self.__df_previos[self.__df_previos["ESTADO"] == self.ESTADO_INACTIVO].reset_index(drop=True)

        if "Id_BANNER" not in self.__df_egresados.columns:
            raise ValueError("No existe la columna Id_BANNER en el archivo de egresados.")

        self.__df_inactivos["ESTADO"] = self.__df_inactivos["ID_BANNER"].isin(self.__df_egresados["Id_BANNER"]).map(
            {True: self.ESTADO_GRADUADO, False: self.ESTADO_INACTIVO}
        )
        self.__df_graduados = self.__df_inactivos[self.__df_inactivos["ESTADO"] == self.ESTADO_GRADUADO].reset_index(drop=True)
        self.__df_inactivos = self.__df_inactivos[self.__df_inactivos["ESTADO"] == self.ESTADO_INACTIVO].reset_index(drop=True)
        self.__df_inactivos = self.__df_inactivos.sort_values("NIVEL_POR_MATERIAS").reset_index(drop=True)

        df_grades = self._build_grades_metrics()
        self.__df_inactivos = pd.merge(
            self.__df_inactivos,
            df_grades,
            left_on="ID_BANNER",
            right_on="id_banner_estudiante",
            how="left",
        ).drop(columns="id_banner_estudiante", errors="ignore")

    def _prepare_reingresos(self):
        self.__df_actuales["ESTADO"] = self.__df_actuales["ID_BANNER"].isin(self.__df_previos["ID_BANNER"]).map(
            {True: self.ESTADO_ANTIGUO, False: self.ESTADO_REINGRESO}
        )
        self.__df_actuales.loc[self.__df_actuales["DENOMINACION_A_N"] == self.DENOMINACION_NUEVO, "ESTADO"] = self.ESTADO_NUEVO
        self.__df_reingreso = self.__df_actuales[
            self.__df_actuales["ESTADO"] == self.ESTADO_REINGRESO
        ].reset_index(drop=True)

    def _build_informe_dataframe(self):
        self.__df_informe = pd.concat([self.__df_desertores, self.__df_inactivos, self.__df_reingreso]).reset_index(
            drop=True
        )
        self.__df_informe["Nombre"] = self._build_nombre_series(self.__df_informe)

    def _build_periodos(self, periodo):

        mapa_ciclos = {
            61: (anio - 1, 66),
            66: (anio, 61),
            12: (anio -1, 16),
            16: (anio, 12)
            }

        anio_prev, ciclo_prev = mapa_ciclos.get(ciclo, (anio, 61))
        anio = int(str(periodo)[:4])
        ciclo = int(str(periodo)[4:])
        return {
            "actual": str(periodo),
            "referencia": f"{anio-2}{ciclo}",
            "previo": f"{anio-1}66" if ciclo == 61 else f"{anio}61",
        }

    def _get_period_dataframe(self, df, periodo, required=False):
        periodo_col = df["PERIODO"].astype(str)
        rows = df[periodo_col == periodo].reset_index(drop=True)
        if required and rows.empty:
            raise ValueError(f"No existen registros del periodo requerido {periodo} en inscritos.")
        return rows

    def _require_columns(self, df, cols, name):
        missing = [c for c in cols if c not in df.columns]
        if missing:
            raise ValueError(
                f"Faltan columnas en {name}: {missing}. "
                f"Columnas disponibles: {list(df.columns)}"
            )

    def _read_csv(self, path, sep=None):
        if sep is None:
            sep = self.__sep
        return pd.read_csv(path, sep=sep)

    def _filter_programa(self, df):
        if self.__programa is None:
            return df
        if "PROGRAMA" not in df.columns:
            raise ValueError("No existe la columna PROGRAMA para filtrar por carrera.")
        return df[df["PROGRAMA"] == self.__programa].reset_index(drop=True)

    def load_data(self, show=False, debug=False):
        self.__df_inscritos = self._read_csv(self.__paths["inscritos"])
        self.__df_egresados = self._read_csv(self.__paths["egresados"], sep=";")
        self.__df_grades = self._read_csv(self.__paths["grades"], sep=";")

        select_cols = list(self.__columnas)
        if self.__programa is not None:
            select_cols.append("PROGRAMA")

        self._require_columns(self.__df_inscritos, select_cols, "inscritos")
        if "PERIODO" not in self.__df_inscritos.columns:
            raise ValueError("No existe la columna PERIODO en el archivo consolidado de inscritos.")

        periodos = self.__periodos
        periodos_presentes = set(self.__df_inscritos["PERIODO"].astype(str).unique())
        faltantes = [p for p in [periodos["actual"]] if p not in periodos_presentes]
        if faltantes:
            raise ValueError(f"Faltan periodos en inscritos: {faltantes}.")

        if "codigo_periodo" in self.__df_grades.columns:
            grades_periodos = set(self.__df_grades["codigo_periodo"].astype(str).unique())
            if periodos["previo"] not in grades_periodos:
                raise ValueError(
                    f"El archivo de calificaciones no contiene el periodo previo {periodos['previo']} "
                    f"(periodos encontrados: {sorted(grades_periodos)})."
                )

        self.__df_inscritos = self.__df_inscritos[select_cols]
        self.__df_inscritos = self._filter_programa(self.__df_inscritos)

        self.__df_referencia = self._get_period_dataframe(self.__df_inscritos, periodos["referencia"], required=False)
        self.__df_actuales = self._get_period_dataframe(self.__df_inscritos, periodos["actual"], required=True)
        self.__df_previos = self._get_period_dataframe(self.__df_inscritos, periodos["previo"], required=False)

        self.__df_referencia["DENOMINACION_A_N"] = self.__df_referencia["DENOMINACION_A_N"].astype("string").str.strip()
        self.__df_actuales["DENOMINACION_A_N"] = self.__df_actuales["DENOMINACION_A_N"].astype("string").str.strip()
        self.__df_previos["DENOMINACION_A_N"] = self.__df_previos["DENOMINACION_A_N"].astype("string").str.strip()

        if debug == True:
            print("load_data:")
            print(f"- referencia filas: {len(self.__df_referencia)}")
            print(f"- actuales filas: {len(self.__df_actuales)}")
            print(f"- previos filas: {len(self.__df_previos)}")
            print(f"- tipo archivo calificaciones: {self._detect_grades_file_type(self.__df_grades)}")

        if show == True:
            display(self.__df_referencia.sample(min(2, len(self.__df_referencia))))
            display(self.__df_actuales.sample(min(2, len(self.__df_actuales))))
            display(self.__df_previos.sample(min(2, len(self.__df_previos))))

    def prepare_data(self, show=False, debug=False):
        if self.__df_referencia is None or self.__df_actuales is None or self.__df_previos is None:
            raise RuntimeError("Ejecuta load_data() antes de prepare_data().")

        self.__df_nuevos = self.__df_actuales[
            self.__df_actuales["DENOMINACION_A_N"] == self.DENOMINACION_NUEVO
        ].reset_index(drop=True)
        self._prepare_desertores()
        self._prepare_inactivos()
        self._prepare_reingresos()
        self._build_informe_dataframe()

        if debug == True:
            print("prepare_data:")
            print(f"- desertores: {len(self.__df_desertores)}")
            print(f"- inactivos: {len(self.__df_inactivos)}")
            print(f"- reingreso: {len(self.__df_reingreso)}")
            print(f"- tasa desercion: {self.__tasa_desercion}")

        if show == True:
            display(self.__df_informe.sample(min(2, len(self.__df_informe))))

    def get_listado(self, table_name="desercion_listado"):
        self._tables_dir.mkdir(parents=True, exist_ok=True)
        df_table = self._build_listado_dataframe()
        latex_table = self.dataframe_to_latex(
            df_table,
            caption=self.CAPTION_LISTADO,
            label=self.LABEL_LISTADO,
            h_align=["c", "l", "l", "l", "l", "l", "l", "l"],
            v_align=["m"] * 8,
            scale=[0.55, 3.2, 1.6, 1.0, 1.1, 1.1, 2.0, 2.4],
        )
        latex_table = latex_table.replace("N°", r"N\textsuperscript{o}")

        table_file = self._tables_dir / f"{table_name}.tex"
        with open(table_file, "w", encoding="utf-8") as f:
            f.write(latex_table)

        return df_table.copy()

    def get_inactivos(self, export_path=None):
        if self.__df_inactivos is None:
            raise RuntimeError("Ejecuta load_data() y prepare_data() antes de pedir los dataframes.")

        df_out = self.__df_inactivos.copy()
        df_out["PERIODO"] = self.__periodos["actual"]

        if export_path is not None:
            df_out.to_csv(export_path, index=False, encoding="utf-8")

        return df_out

    def plot_estadisticas(self, figname="image"):
        if self.__df_informe is None:
            raise RuntimeError("Ejecuta load_data() y prepare_data() antes de graficar.")

        conteos = {
            "Desertores": len(self.__df_desertores),
            "Nuevos": len(self.__df_nuevos),
            "Actuales": len(self.__df_actuales),
            "Previos": len(self.__df_previos),
            "Graduados": len(self.__df_graduados),
            "Inactivos": len(self.__df_inactivos),
            "Reingresos": len(self.__df_reingreso),
        }
        self.__conteos = conteos
        df_conteos = pd.DataFrame(list(conteos.items()), columns=["Grupo", "Cantidad"])

        fig_path = self._image_path / f"{figname}.png"

        plt.figure(figsize=(8, 5))
        if sns is not None:
            ax = sns.barplot(data=df_conteos, x="Grupo", y="Cantidad", palette="Set3", hue="Grupo")
        else:
            ax = df_conteos.plot(kind="bar", x="Grupo", y="Cantidad", color="#8FB9A8", legend=False)

        for p in ax.patches:
            ax.text(
                p.get_x() + p.get_width() / 2,
                p.get_height() + 0.5,
                int(p.get_height()),
                ha="center",
            )

        plt.tight_layout()
        plt.savefig(fig_path, dpi=300, bbox_inches="tight")
        plt.show()

        return fig_path

    def get_estadisticas(self):
        if self.__conteos is None:
            raise RuntimeError("Ejecuta plot_estadisticas() antes de pedir conteos.")
        return self.__conteos.copy()

    def get_tasa_desercion(self):
        if self.__tasa_desercion is None:
            raise RuntimeError("Ejecuta load_data() y prepare_data() antes de pedir la tasa.")
        return self.__tasa_desercion

    def run_outputs(self, show=False, debug=False, fig_name="image"):
        if self.__df_referencia is None:
            self.load_data(show=show, debug=debug)
        if self.__df_informe is None:
            self.prepare_data(show=show, debug=debug)

        fig_path = self.plot_estadisticas(figname=fig_name)
        listado = self.get_listado()

        return {
            "fig_estadisticas": fig_path,
            "listado": listado,
            "tasa_desercion": self.__tasa_desercion,
            "conteos": self.__conteos,
        }
