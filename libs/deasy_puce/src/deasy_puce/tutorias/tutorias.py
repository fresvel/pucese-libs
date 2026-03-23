import pandas as pd
import matplotlib.pyplot as plt
from textwrap import fill

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


class InformeTutorias(Informe):
    def __init__(
        self,
        periodo,
        tutorias_path,
        programa=None,
        titulo="Informe de Tutorias",
        image_path="../Latex/Contenido/images/",
    ):
        super().__init__(periodo, titulo=titulo)

        self.__tutorias_path = tutorias_path
        self.__programa = programa
        self._image_path = self._resolve_image_path(image_path)

        self.__required_columns = [
            "periodo",
            "Programa",
            "nrc",
            "titulo_asignatura",
            "id_docente",
            "apellido_docente",
            "primer_nombre_docente",
            "segundo_nombre_docente",
            "fecha_tutoria_registrada",
            "desc_tipo_tutoria",
            "desc_modalidad_tutoria",
            "codigo_ambito_tutoria",
            "desc_ambito_tipo_tutoria",
            "tema",
            "observaciones",
            "acuerdos",
        ]
        self.__df_raw = None
        self.__df_tutorias = None
        self.__resumen_docente = None
        self.__resumen_docente_tipo = None
        self.__resumen_tipo = None
        self.__resumen_modalidad = None
        self.__resumen_modalidad_tipo = None
        self.__resumen_ambito = None
        self.__resumen_ambito_tipo = None
        self.__resumen_ambito_modalidad = None
        self.__resumen_asignatura = None
        self.__metadata = None

    def _resolve_image_path(self, image_path):
        fallback = Path(self._save_path) / "images"
        candidates = []

        if image_path is not None:
            candidates.append(Path(image_path))
        candidates.append(fallback)

        last_error = None
        for candidate in candidates:
            try:
                candidate.mkdir(parents=True, exist_ok=True)
                return candidate
            except OSError as exc:
                last_error = exc

        if last_error is not None:
            raise last_error
        raise OSError("No se pudo inicializar un directorio de imágenes para tutorías.")

    def _require_columns(self, df, cols, name):
        missing = [c for c in cols if c not in df.columns]
        if missing:
            raise ValueError(
                f"Faltan columnas en {name}: {missing}. "
                f"Columnas disponibles: {list(df.columns)}"
            )

    def _read_csv(self, path):
        last_error = None
        for encoding in ["utf-8", "latin-1"]:
            for sep in [";", ","]:
                try:
                    df = pd.read_csv(path, sep=sep, encoding=encoding, low_memory=False)
                    if df.shape[1] > 1 or sep == ",":
                        return df
                except Exception as exc:
                    last_error = exc
        if last_error is not None:
            raise last_error
        return pd.read_csv(path, low_memory=False)

    def _empty_table_df(self, message="No se encontraron datos."):
        return pd.DataFrame({"Mensaje": [message]})

    def _write_table(self, df, table_name, caption, label, empty_message="No se encontraron datos."):
        self._tables_dir.mkdir(parents=True, exist_ok=True)

        if df is None or df.empty:
            df_table = self._empty_table_df(empty_message)
        else:
            df_table = df.fillna("-")

        table = self.dataframe_to_latex(
            df_table,
            caption=caption,
            label=label,
            set_caption="empty",
        )

        if table == "":
            return None

        table_file = self._tables_dir / f"{table_name}.tex"
        with open(table_file, "w", encoding="utf-8") as file:
            file.write(table)

        return table_file

    def _clean_text(self, series):
        return (
            series.fillna("")
            .astype(str)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
        )

    def _normalize_value(self, value):
        if value is None:
            return None
        return " ".join(str(value).split()).strip()

    def _filter_programa(self, df):
        if self.__programa is None:
            return df.reset_index(drop=True)

        programa_objetivo = self._normalize_value(self.__programa)
        programa_series = self._clean_text(df["Programa"])
        df_filtrado = df[programa_series == programa_objetivo].reset_index(drop=True)

        if df_filtrado.empty:
            disponibles = sorted(programa_series[programa_series != ""].drop_duplicates().tolist())
            muestra = disponibles[:15]
            raise ValueError(
                f"No se encontraron registros para el programa '{programa_objetivo}' "
                f"en el periodo {self._periodo['actual']}. Programas disponibles: {muestra}"
            )

        return df_filtrado

    def _prepare_categorical_summary(self, column, label):
        summary = (
            self.__df_tutorias.groupby(column, dropna=False)
            .size()
            .reset_index(name="Numero_Tutorias")
        )
        summary[column] = self._clean_text(summary[column]).replace("", "Sin dato")
        summary = summary.sort_values(
            by=["Numero_Tutorias", column],
            ascending=[False, True],
        ).reset_index(drop=True)
        summary = summary.rename(columns={column: label})
        return summary

    def _prepare_type_breakdown(self, column, wrap_width=None):
        summary = (
            self.__df_tutorias.groupby([column, "Tipo"], dropna=False)
            .size()
            .reset_index(name="Numero_Tutorias")
        )
        summary[column] = self._clean_text(summary[column]).replace("", "Sin dato")
        summary["Tipo"] = self._clean_text(summary["Tipo"]).replace("", "Sin dato")
        summary["Total"] = summary.groupby(column)["Numero_Tutorias"].transform("sum")
        summary = summary.sort_values(
            by=["Total", column, "Tipo"],
            ascending=[False, True, True],
        ).reset_index(drop=True)

        if wrap_width is not None:
            summary["Etiqueta"] = summary[column].apply(
                lambda value: fill(str(value), width=wrap_width, break_long_words=False)
            )
        else:
            summary["Etiqueta"] = summary[column]

        return summary

    def _plot_stacked_by_tipo(
        self,
        df,
        label_col,
        value_col,
        title,
        xlabel,
        ylabel,
        figname,
        horizontal=False,
    ):
        if df is None or df.empty:
            return None

        if sns is not None:
            sns.set_theme(style="whitegrid", palette="Set2")
            colors = sns.color_palette("Set2", n_colors=df.shape[1])
        else:
            colors = plt.get_cmap("Set2").colors[:df.shape[1]]

        save_path = self._image_path / f"{figname}.png"
        fig_height = max(4.5, min(14, 0.6 * len(df) + 1.8))
        fig_width = 12 if horizontal else max(8, min(16, 0.8 * len(df) + 3))
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))

        if horizontal:
            df.plot(
                kind="barh",
                stacked=True,
                ax=ax,
                color=colors,
                width=0.8,
            )
            totals = df.sum(axis=1)
            for idx, total in enumerate(totals):
                ax.text(total + 0.3, idx, f"{int(total)}", va="center", ha="left", fontsize=9)
            ax.grid(axis="x", linestyle="--", alpha=0.25)
        else:
            df.plot(
                kind="bar",
                stacked=True,
                ax=ax,
                color=colors,
                width=0.7,
            )
            totals = df.sum(axis=1)
            for idx, total in enumerate(totals):
                ax.text(idx, total + 0.3, f"{int(total)}", va="bottom", ha="center", fontsize=9)
            ax.grid(axis="y", linestyle="--", alpha=0.25)
            ax.tick_params(axis="x", rotation=0)

        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.legend(title="Tipo de tutoría")
        fig.tight_layout()
        fig.savefig(save_path, dpi=300, bbox_inches="tight")
        if "agg" not in plt.get_backend().lower():
            plt.show()
        plt.close(fig)

        return save_path

    def _plot_stacked_by_modalidad(
        self,
        df,
        title,
        xlabel,
        ylabel,
        figname,
        horizontal=False,
    ):
        if df is None or df.empty:
            return None

        if sns is not None:
            sns.set_theme(style="whitegrid", palette="Set2")
            colors = sns.color_palette("Set2", n_colors=df.shape[1])
        else:
            colors = plt.get_cmap("Set2").colors[:df.shape[1]]

        save_path = self._image_path / f"{figname}.png"
        fig_height = max(4.5, min(14, 0.6 * len(df) + 1.8))
        fig_width = 12 if horizontal else max(8, min(16, 0.8 * len(df) + 3))
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))

        if horizontal:
            df.plot(kind="barh", stacked=True, ax=ax, color=colors, width=0.8)
            totals = df.sum(axis=1)
            for idx, total in enumerate(totals):
                ax.text(total + 0.3, idx, f"{int(total)}", va="center", ha="left", fontsize=9)
            ax.grid(axis="x", linestyle="--", alpha=0.25)
        else:
            df.plot(kind="bar", stacked=True, ax=ax, color=colors, width=0.7)
            totals = df.sum(axis=1)
            for idx, total in enumerate(totals):
                ax.text(idx, total + 0.3, f"{int(total)}", va="bottom", ha="center", fontsize=9)
            ax.grid(axis="y", linestyle="--", alpha=0.25)
            ax.tick_params(axis="x", rotation=0)

        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.legend(title="Modalidad")
        fig.tight_layout()
        fig.savefig(save_path, dpi=300, bbox_inches="tight")
        if "agg" not in plt.get_backend().lower():
            plt.show()
        plt.close(fig)

        return save_path

    def _plot_count_chart(
        self,
        df,
        category_col,
        value_col,
        xlabel,
        ylabel,
        title,
        figname,
        horizontal=False,
        color="#2D6A4F",
    ):
        if df is None or df.empty:
            return None

        save_path = self._image_path / f"{figname}.png"
        fig_height = max(4.5, min(12, 0.55 * len(df) + 1.8))
        fig_width = 12 if horizontal else max(8, min(18, 0.8 * len(df) + 3))
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))

        plot_df = df.copy()

        if sns is not None:
            if horizontal:
                sns.barplot(
                    data=plot_df,
                    x=value_col,
                    y=category_col,
                    ax=ax,
                    color=color,
                )
            else:
                sns.barplot(
                    data=plot_df,
                    x=category_col,
                    y=value_col,
                    ax=ax,
                    color=color,
                )
        else:
            if horizontal:
                ax.barh(plot_df[category_col], plot_df[value_col], color=color)
            else:
                ax.bar(plot_df[category_col], plot_df[value_col], color=color)

        if horizontal:
            for patch in ax.patches:
                width = patch.get_width()
                ax.text(
                    width + 0.3,
                    patch.get_y() + patch.get_height() / 2,
                    f"{int(width)}",
                    va="center",
                    ha="left",
                    fontsize=9,
                )
        else:
            for patch in ax.patches:
                height = patch.get_height()
                ax.text(
                    patch.get_x() + patch.get_width() / 2,
                    height + 0.3,
                    f"{int(height)}",
                    va="bottom",
                    ha="center",
                    fontsize=9,
                )
            ax.tick_params(axis="x", rotation=30)

        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.grid(axis="x" if horizontal else "y", linestyle="--", alpha=0.25)
        fig.tight_layout()
        fig.savefig(save_path, dpi=300, bbox_inches="tight")
        if "agg" not in plt.get_backend().lower():
            plt.show()
        plt.close(fig)

        return save_path

    def load_data(self, show=False, debug=False):
        try:
            self.__df_raw = self._read_csv(self.__tutorias_path)
            self._require_columns(self.__df_raw, self.__required_columns, "tutorias")

            self.__df_raw = self.__df_raw.copy()
            self.__df_raw["periodo"] = self._clean_text(self.__df_raw["periodo"])
            periodo_actual = str(self._periodo["actual"])
            self.__df_raw = self.__df_raw[self.__df_raw["periodo"] == periodo_actual].reset_index(drop=True)
            self.__df_raw["Programa"] = self._clean_text(self.__df_raw["Programa"])

            if self.__df_raw.empty:
                raise ValueError(
                    f"El archivo no contiene registros para el periodo {periodo_actual}."
                )

            self.__df_raw = self._filter_programa(self.__df_raw)

            if debug == True:
                print("load_data (tutorias):")
                print(f"- filas archivo: {len(self.__df_raw)}")
                print(f"- programa: {self.__programa if self.__programa is not None else 'TODOS'}")
                print(f"- columnas: {list(self.__df_raw.columns)}")

            if show == True:
                display(self.__df_raw.sample(min(2, len(self.__df_raw))))

        except FileNotFoundError:
            raise FileNotFoundError(
                f"No se encontró el archivo de tutorías: {self.__tutorias_path}"
            )
        except Exception as exc:
            raise RuntimeError(
                "No se pudo cargar/procesar el archivo de Tutorías.\n"
                f"Detalle: {exc}"
            )

    def prepare_data(self, show=False, debug=False):
        if self.__df_raw is None:
            raise RuntimeError("Ejecuta load_data() antes de prepare_data().")

        df = self.__df_raw.copy()

        for column in self.__required_columns:
            df[column] = self._clean_text(df[column])

        df["Docente"] = (
            df["apellido_docente"]
            + " "
            + df["primer_nombre_docente"]
            + " "
            + df["segundo_nombre_docente"]
        )
        df["Docente"] = (
            self._clean_text(df["Docente"])
            .str.replace("/", " ", regex=False)
            .apply(self.text_title_case)
            .replace("", "Sin dato")
        )
        df["Tipo"] = self._clean_text(df["desc_tipo_tutoria"]).replace("", "Sin dato")
        df["Modalidad"] = self._clean_text(df["desc_modalidad_tutoria"]).replace("", "Sin dato")
        df["Codigo_Ambito"] = self._clean_text(df["codigo_ambito_tutoria"]).replace("", "Sin dato")
        df["Ambito"] = self._clean_text(df["desc_ambito_tipo_tutoria"]).replace("", "Sin dato")
        df["Asignatura"] = (
            self._clean_text(df["titulo_asignatura"])
            .apply(self.text_title_case)
            .replace("", "Sin dato")
        )

        self.__df_tutorias = df.reset_index(drop=True)

        self.__resumen_docente = self._prepare_categorical_summary("Docente", "Docente")
        self.__resumen_tipo = self._prepare_categorical_summary("Tipo", "Tipo")
        self.__resumen_modalidad = self._prepare_categorical_summary("Modalidad", "Modalidad")
        self.__resumen_docente_tipo = self._prepare_type_breakdown("Docente")
        self.__resumen_modalidad_tipo = self._prepare_type_breakdown("Modalidad")

        self.__resumen_ambito = (
            self.__df_tutorias.groupby(["Codigo_Ambito", "Ambito"], dropna=False)
            .size()
            .reset_index(name="Numero_Tutorias")
        )
        self.__resumen_ambito["Codigo_Ambito"] = self._clean_text(
            self.__resumen_ambito["Codigo_Ambito"]
        ).replace("", "Sin dato")
        self.__resumen_ambito["Ambito"] = self._clean_text(
            self.__resumen_ambito["Ambito"]
        ).replace("", "Sin dato")
        self.__resumen_ambito["Ambito_Etiqueta"] = (
            self.__resumen_ambito["Codigo_Ambito"]
            + " - "
            + self.__resumen_ambito["Ambito"]
        )
        self.__resumen_ambito = self.__resumen_ambito.sort_values(
            by=["Numero_Tutorias", "Codigo_Ambito", "Ambito"],
            ascending=[False, True, True],
        ).reset_index(drop=True)
        self.__resumen_ambito_tipo = self._prepare_type_breakdown("Ambito", wrap_width=32)
        self.__resumen_ambito_modalidad = (
            self.__df_tutorias.groupby(["Ambito", "Tipo", "Modalidad"], dropna=False)
            .size()
            .reset_index(name="Numero_Tutorias")
        )
        self.__resumen_ambito_modalidad["Ambito"] = self._clean_text(
            self.__resumen_ambito_modalidad["Ambito"]
        ).replace("", "Sin dato")
        self.__resumen_ambito_modalidad["Tipo"] = self._clean_text(
            self.__resumen_ambito_modalidad["Tipo"]
        ).replace("", "Sin dato")
        self.__resumen_ambito_modalidad["Modalidad"] = self._clean_text(
            self.__resumen_ambito_modalidad["Modalidad"]
        ).replace("", "Sin dato")
        self.__resumen_ambito_modalidad["Etiqueta"] = self.__resumen_ambito_modalidad["Ambito"].apply(
            lambda value: fill(str(value), width=32, break_long_words=False)
        )

        self.__resumen_asignatura = (
            self.__df_tutorias.groupby(["Docente", "Asignatura"], dropna=False)
            .size()
            .reset_index(name="Numero_Tutorias")
        )
        self.__resumen_asignatura["Docente"] = self._clean_text(
            self.__resumen_asignatura["Docente"]
        ).replace("", "Sin dato")
        self.__resumen_asignatura["Asignatura"] = self._clean_text(
            self.__resumen_asignatura["Asignatura"]
        ).replace("", "Sin dato")
        self.__resumen_asignatura = self.__resumen_asignatura.sort_values(
            by=["Asignatura", "Docente", "Numero_Tutorias"],
            ascending=[True, True, False],
        ).reset_index(drop=True)[["Asignatura", "Docente", "Numero_Tutorias"]]

        self.__metadata = {
            "periodo": str(self._periodo["actual"]),
            "programa": self.__programa if self.__programa is not None else "TODOS",
            "registros_csv": int(len(self.__df_raw)),
            "registros_tutorias": int(len(self.__df_tutorias)),
            "docentes": int(self.__resumen_docente["Docente"].nunique()),
            "tipos": int(self.__resumen_tipo["Tipo"].nunique()),
            "modalidades": int(self.__resumen_modalidad["Modalidad"].nunique()),
            "ambitos": int(self.__resumen_ambito["Ambito_Etiqueta"].nunique()),
            "asignaturas": int(self.__df_tutorias["Asignatura"].nunique()),
        }

        if debug == True:
            print("prepare_data (tutorias):")
            print(f"- programa: {self.__metadata['programa']}")
            print(f"- registros csv: {self.__metadata['registros_csv']}")
            print(f"- registros tutorias: {self.__metadata['registros_tutorias']}")
            print(f"- docentes: {self.__metadata['docentes']}")
            print(f"- tipos: {self.__metadata['tipos']}")
            print(f"- modalidades: {self.__metadata['modalidades']}")
            print(f"- ambitos: {self.__metadata['ambitos']}")
            print(f"- asignaturas: {self.__metadata['asignaturas']}")

        if show == True:
            display(self.__df_tutorias.sample(min(2, len(self.__df_tutorias))))

        return {
            "encontrado": not self.__df_tutorias.empty,
            "metadata": self.__metadata.copy(),
            "tutorias": self.__df_tutorias.copy(),
        }

    def plot_tutorias_por_docente(self, figname="tutorias_por_docente"):
        if self.__resumen_docente_tipo is None:
            raise RuntimeError("Primero ejecuta prepare_data() antes de graficar.")
        pivot = (
            self.__resumen_docente_tipo.pivot_table(
                index="Etiqueta",
                columns="Tipo",
                values="Numero_Tutorias",
                aggfunc="sum",
                fill_value=0,
            )
        )
        return self._plot_stacked_by_tipo(
            pivot,
            label_col="Etiqueta",
            value_col="Numero_Tutorias",
            title="Numero de tutorias por docente y tipo",
            xlabel="Numero de tutorias",
            ylabel="Docente",
            figname=figname,
            horizontal=True,
        )

    def plot_tutorias_por_modalidad(self, figname="tutorias_por_modalidad"):
        if self.__resumen_modalidad_tipo is None:
            raise RuntimeError("Primero ejecuta prepare_data() antes de graficar.")
        pivot = (
            self.__resumen_modalidad_tipo.pivot_table(
                index="Etiqueta",
                columns="Tipo",
                values="Numero_Tutorias",
                aggfunc="sum",
                fill_value=0,
            )
        )
        return self._plot_stacked_by_tipo(
            pivot,
            label_col="Etiqueta",
            value_col="Numero_Tutorias",
            title="Numero de tutorias por modalidad y tipo",
            xlabel="Modalidad",
            ylabel="Numero de tutorias",
            figname=figname,
        )

    def _plot_tutorias_por_ambito_y_tipo(self, tipo, figname, title):
        if self.__resumen_ambito_modalidad is None:
            raise RuntimeError("Primero ejecuta prepare_data() antes de graficar.")
        df_tipo = self.__resumen_ambito_modalidad[
            self.__resumen_ambito_modalidad["Tipo"] == tipo
        ].copy()
        if df_tipo.empty:
            return None
        pivot = (
            df_tipo.pivot_table(
                index="Etiqueta",
                columns="Modalidad",
                values="Numero_Tutorias",
                aggfunc="sum",
                fill_value=0,
            )
        )
        return self._plot_stacked_by_modalidad(
            pivot,
            title=title,
            xlabel="Numero de tutorias",
            ylabel="Ambito",
            figname=figname,
            horizontal=True,
        )

    def plot_tutorias_por_ambito_academica(self, figname="tutorias_por_ambito_academica"):
        return self._plot_tutorias_por_ambito_y_tipo(
            "Tutoría Académica",
            figname=figname,
            title="Numero de tutorias academicas por ambito y modalidad",
        )

    def plot_tutorias_por_ambito_mentoria(self, figname="tutorias_por_ambito_mentoria"):
        return self._plot_tutorias_por_ambito_y_tipo(
            "Mentoría",
            figname=figname,
            title="Numero de mentorias por ambito y modalidad",
        )

    def get_tutorias_por_docente(self):
        if self.__resumen_docente is None:
            raise RuntimeError("Ejecuta load_data() y prepare_data() antes de pedir los dataframes.")
        return self.__resumen_docente.copy()

    def get_tutorias_por_tipo(self):
        if self.__resumen_tipo is None:
            raise RuntimeError("Ejecuta load_data() y prepare_data() antes de pedir los dataframes.")
        return self.__resumen_tipo.copy()

    def get_tutorias_por_modalidad(self):
        if self.__resumen_modalidad is None:
            raise RuntimeError("Ejecuta load_data() y prepare_data() antes de pedir los dataframes.")
        return self.__resumen_modalidad.copy()

    def get_tutorias_por_ambito(self):
        if self.__resumen_ambito is None:
            raise RuntimeError("Ejecuta load_data() y prepare_data() antes de pedir los dataframes.")
        return self.__resumen_ambito.copy()

    def get_tutorias_por_asignatura(self, table_name="tutorias_por_asignatura"):
        if self.__resumen_asignatura is None:
            raise RuntimeError("Ejecuta load_data() y prepare_data() antes de pedir los dataframes.")

        df_table = self.__resumen_asignatura.rename(
            columns={
                "Asignatura": "Asignatura",
                "Docente": "Docente",
                "Numero_Tutorias": "Numero de Tutorias",
            }
        )

        self._write_table(
            df_table,
            table_name=table_name,
            caption="Numero de tutorias por docente y asignatura",
            label=table_name,
        )

        return df_table.copy()

    def get_metadata(self):
        if self.__metadata is None:
            raise RuntimeError("Ejecuta load_data() y prepare_data() antes de pedir el resumen.")
        return self.__metadata.copy()

    def get_programas_disponibles(self):
        if self.__df_raw is not None:
            programas = self.__df_raw["Programa"]
        else:
            df = self._read_csv(self.__tutorias_path)
            self._require_columns(df, ["periodo", "Programa"], "tutorias")
            df = df.copy()
            df["periodo"] = self._clean_text(df["periodo"])
            df = df[df["periodo"] == str(self._periodo["actual"])].reset_index(drop=True)
            programas = self._clean_text(df["Programa"])

        return sorted(programas[programas != ""].drop_duplicates().tolist())

    def run_outputs(
        self,
        show=False,
        debug=False,
        docente_fig="tutorias_por_docente",
        modalidad_fig="tutorias_por_modalidad",
        ambito_academica_fig="tutorias_por_ambito_academica",
        ambito_mentoria_fig="tutorias_por_ambito_mentoria",
        asignatura_table="tutorias_por_asignatura",
    ):
        if self.__df_raw is None:
            self.load_data(show=show, debug=debug)
        elif debug == True:
            print("run_outputs (tutorias): usando datos cargados")

        if self.__df_tutorias is None:
            prep = self.prepare_data(show=show, debug=debug)
        else:
            prep = {"encontrado": not self.__df_tutorias.empty}
            if debug == True:
                print("run_outputs (tutorias): usando datos preparados")

        omitio_graficos = False
        if not prep.get("encontrado", True):
            fig_docente = None
            fig_modalidad = None
            fig_ambito_academica = None
            fig_ambito_mentoria = None
            omitio_graficos = True
        else:
            fig_docente = self.plot_tutorias_por_docente(figname=docente_fig)
            fig_modalidad = self.plot_tutorias_por_modalidad(figname=modalidad_fig)
            fig_ambito_academica = self.plot_tutorias_por_ambito_academica(
                figname=ambito_academica_fig
            )
            fig_ambito_mentoria = self.plot_tutorias_por_ambito_mentoria(
                figname=ambito_mentoria_fig
            )

        tabla_asignatura = self.get_tutorias_por_asignatura(table_name=asignatura_table)

        return {
            "fig_docente": fig_docente,
            "fig_modalidad": fig_modalidad,
            "fig_ambito_academica": fig_ambito_academica,
            "fig_ambito_mentoria": fig_ambito_mentoria,
            "tabla_asignatura": tabla_asignatura,
            "resumen_docente": self.get_tutorias_por_docente(),
            "resumen_tipo": self.get_tutorias_por_tipo(),
            "resumen_modalidad": self.get_tutorias_por_modalidad(),
            "resumen_ambito": self.get_tutorias_por_ambito(),
            "metadata": self.get_metadata(),
            "graficos_omitidos": omitio_graficos,
            "encontrado": prep.get("encontrado", True),
        }


InformeTutorías = InformeTutorias
