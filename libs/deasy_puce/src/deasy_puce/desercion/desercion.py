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
    def __init__(
        self,
        periodo,
        programa,
        inscritos_path,
        egresados_path,
        grades_path,
        sep=";",
        image_path="../Latex/Contenido/Images/",
    ):
        super().__init__(periodo, titulo="Informe de Deserción Estudiantil")

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

    def _build_periodos(self, periodo):
        anio = int(str(periodo)[:4])
        ciclo = int(str(periodo)[4:])
        return {
            "actual": str(periodo),
            "referencia": f"{anio-2}{ciclo}",
            "previo": f"{anio-1}66" if ciclo == 61 else f"{anio}61",
        }

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
        faltantes = [p for p in [periodos["referencia"], periodos["actual"], periodos["previo"]] if p not in periodos_presentes]
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

        periodo_col = self.__df_inscritos["PERIODO"].astype(str)
        self.__df_referencia = self.__df_inscritos[periodo_col == periodos["referencia"]].reset_index(drop=True)
        self.__df_actuales = self.__df_inscritos[periodo_col == periodos["actual"]].reset_index(drop=True)
        self.__df_previos = self.__df_inscritos[periodo_col == periodos["previo"]].reset_index(drop=True)

        self.__df_referencia["DENOMINACION_A_N"] = self.__df_referencia["DENOMINACION_A_N"].str.strip()
        self.__df_actuales["DENOMINACION_A_N"] = self.__df_actuales["DENOMINACION_A_N"].str.strip()

        if debug == True:
            print("load_data:")
            print(f"- referencia filas: {len(self.__df_referencia)}")
            print(f"- actuales filas: {len(self.__df_actuales)}")
            print(f"- previos filas: {len(self.__df_previos)}")

        if show == True:
            display(self.__df_referencia.sample(min(2, len(self.__df_referencia))))
            display(self.__df_actuales.sample(min(2, len(self.__df_actuales))))
            display(self.__df_previos.sample(min(2, len(self.__df_previos))))

    def prepare_data(self, show=False, debug=False):
        if self.__df_referencia is None or self.__df_actuales is None or self.__df_previos is None:
            raise RuntimeError("Ejecuta load_data() antes de prepare_data().")

        self.__df_nuevos = self.__df_actuales[self.__df_actuales["DENOMINACION_A_N"] == "NUEVO"].reset_index(drop=True)

        self.__df_referencia = self.__df_referencia[self.__df_referencia["DENOMINACION_A_N"] == "NUEVO"].reset_index(drop=True)
        self.__df_referencia["ESTADO"] = self.__df_referencia["ID_BANNER"].isin(self.__df_actuales["ID_BANNER"]).map(
            {True: "Activo", False: "Deserción"}
        )
        self.__df_desertores = self.__df_referencia[self.__df_referencia["ESTADO"] == "Deserción"].reset_index(drop=True)

        base = self.__df_referencia["ID_BANNER"].count()
        self.__tasa_desercion = (self.__df_desertores["ID_BANNER"].size / base) if base else 0

        self.__df_previos["ESTADO"] = self.__df_previos["ID_BANNER"].isin(self.__df_actuales["ID_BANNER"]).map(
            {True: "Activo", False: "Inactivo"}
        )
        self.__df_inactivos = self.__df_previos[self.__df_previos["ESTADO"] == "Inactivo"].reset_index(drop=True)

        if "Id_BANNER" not in self.__df_egresados.columns:
            raise ValueError("No existe la columna Id_BANNER en el archivo de egresados.")
        self.__df_inactivos["ESTADO"] = self.__df_inactivos["ID_BANNER"].isin(self.__df_egresados["Id_BANNER"]).map(
            {True: "Graduado", False: "Inactivo"}
        )
        self.__df_graduados = self.__df_inactivos[self.__df_inactivos["ESTADO"] == "Graduado"].reset_index(drop=True)
        self.__df_inactivos = self.__df_inactivos[self.__df_inactivos["ESTADO"] == "Inactivo"].reset_index(drop=True)
        self.__df_inactivos = self.__df_inactivos.sort_values("NIVEL_POR_MATERIAS").reset_index(drop=True)

        if "id_banner_estudiante" in self.__df_grades.columns:
            df_means = (
                self.__df_grades.groupby("id_banner_estudiante")["nota_final"]
                .mean(numeric_only=True)
                .round(2)
                .reset_index(name="mean")
            )
            aprobado = self.__df_grades.groupby("id_banner_estudiante")["estado"].apply(lambda x: (x == "APROBADO").sum())
            reprobado = self.__df_grades.groupby("id_banner_estudiante")["estado"].apply(lambda x: (x == "REPROBADO").sum())
            df_exito = round((100 * aprobado) / (aprobado + reprobado), 2).reset_index(name="exito")
            df_grades = pd.merge(df_means, df_exito, on="id_banner_estudiante")
            self.__df_inactivos = pd.merge(
                self.__df_inactivos, df_grades, left_on="ID_BANNER", right_on="id_banner_estudiante", how="left"
            ).drop(columns="id_banner_estudiante")

        self.__df_actuales["ESTADO"] = self.__df_actuales["ID_BANNER"].isin(self.__df_previos["ID_BANNER"]).map(
            {True: "Antiguo", False: "Reingreso"}
        )
        self.__df_actuales.loc[self.__df_actuales["DENOMINACION_A_N"] == "NUEVO", "ESTADO"] = "Nuevo"
        self.__df_reingreso = self.__df_actuales[self.__df_actuales["ESTADO"] == "Reingreso"].reset_index(drop=True)

        self.__df_informe = pd.concat([self.__df_desertores, self.__df_inactivos, self.__df_reingreso]).reset_index(
            drop=True
        )
        self.__df_informe["Nombre"] = (
            self.__df_informe["APELIDOS"]
            + " "
            + self.__df_informe["PRIMER_NOMBRE"]
            + " "
            + self.__df_informe["SEGUNDO_NOMBRE"]
        )
        self.__df_informe["Nombre"] = self.__df_informe["Nombre"].apply(self.text_title_case)

        if debug == True:
            print("prepare_data:")
            print(f"- desertores: {len(self.__df_desertores)}")
            print(f"- inactivos: {len(self.__df_inactivos)}")
            print(f"- reingreso: {len(self.__df_reingreso)}")
            print(f"- tasa desercion: {self.__tasa_desercion}")

        if show == True:
            display(self.__df_informe.sample(min(2, len(self.__df_informe))))

    def get_listado(self, table_name="desercion_listado"):
        if self.__df_informe is None:
            raise RuntimeError("Ejecuta load_data() y prepare_data() antes de pedir los dataframes.")

        self._tables_dir.mkdir(parents=True, exist_ok=True)

        latex_table = r"""
\begin{longtblr}[
  caption={Listado de estudiantes identificados en deserción o reingreso},
  label={tab:listado_estudiantes}
]{
  colspec={Q[l, m, 4cm] Q[l, m, 2cm] Q[l, m, 1.5cm] Q[l, m, 1.5cm] Q[l, m, 1.5cm] Q[l, m, 4cm]},
  rowhead={1},
  row{1-Z}={font=\normalsize },
  row{1}={bg=colhead!40, font=\normalsize \bfseries },
  vlines,hlines
}
  Estudiante & Estado & Nivel & Promedio & Éxito & Observación \\"""

        if self.__df_informe.empty:
            for nombre, estado, nivel, promedio, exito in [["No se encontraron datos.", "", "", "", ""]]:
                latex_table += f"\n  {nombre} & {estado} & {nivel} & {promedio} & {exito} & \\\\"
        else:
            df_table = self.__df_informe.copy()
            if "mean" not in df_table.columns:
                df_table["mean"] = "-"
            if "exito" not in df_table.columns:
                df_table["exito"] = "-"
            df_table["mean"] = df_table["mean"].fillna("-")
            df_table["exito"] = df_table["exito"].fillna("-")
            df_table["NIVEL_POR_MATERIAS"] = df_table["NIVEL_POR_MATERIAS"].fillna("-")

            for _, row in df_table.iterrows():
                nombre = row.get("Nombre", "")
                estado = row.get("ESTADO", "")
                nivel = row.get("NIVEL_POR_MATERIAS", "")
                promedio = row.get("mean", "-")
                exito = row.get("exito", "-")
                latex_table += f"\n  {nombre} & {estado} & {nivel} & {promedio} & {exito} & \\\\"

        latex_table += "\n\\end{longtblr}"

        table_file = self._tables_dir / f"{table_name}.tex"
        with open(table_file, "w", encoding="utf-8") as f:
            f.write(latex_table)

        return self.__df_informe.copy()

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
