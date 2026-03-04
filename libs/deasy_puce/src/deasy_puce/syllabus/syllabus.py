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


class Syllabus(Informe):
    def __init__(self, periodo, titulo="Informes de Syllabus", image_path="../Latex/Image/"):
        self._image_path = Path(image_path)
        self._image_path.mkdir(parents=True, exist_ok=True)

        super().__init__(periodo, titulo)

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
                    df = pd.read_csv(path, sep=sep, encoding=encoding)
                    if df.shape[1] > 1 or sep == ",":
                        return df
                except Exception as e:
                    last_error = e
        if last_error:
            raise last_error
        return pd.read_csv(path)

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
        with open(table_file, "w", encoding="utf-8") as f:
            f.write(table)

        return table_file


class SyllabusSeguimiento(Syllabus):
    def __init__(self, periodo, programa, szascn_path, notas_path, image_path="../Latex/Image/"):
        super().__init__(periodo, titulo="Informes de Syllabus", image_path=image_path)

        self.__szascn_path = szascn_path
        self.__notas_path = notas_path

        self._semestre = self._months_period
        self.__programa = programa

        self.__notas_select = ["NRC", "NIVEL", "titulo_curso", "cod_programa_estudiante"]
        self.__szascn_select = [
            "PERIODO", "NRC", "TITULO ASIGNATURA",
            "RESULTADO DE APRENDIZAJE DEL PROGRAMA",
            "ID DOCENTE", "APELLIDO DOCENTE",
            "PRIMER NOMBRE DOCENTE", "SEGUNDO NOMBRE DOCENTE",
            "GRADO DE SATISFACIÓN"
        ]

        self.__df_notas = None
        self.__df_nrcs = None
        self.__df_szascn = None

        self.__df_nrcs_sin_seguimiento = None          
        self.__df_nrcs_con_seguimiento = None          
        self.__df_szascn_carrera = None
        self.__df_szascn_otros_programas = None
        self.__df_szascn_del_programa = None
        self.__df_szascn_filtered = None
        self.__df_evaluaciones = None

        self.__df_no_registradas = None                
        self.__df_registradas_otro_programa = None     
        self.__df_registradas_programa = None          
        self.__cumplimiento = None



    def load_data(self, show=False, debug=False):
        try:
            self.__df_notas = self._read_csv(self.__notas_path)
            self._require_columns(self.__df_notas, self.__notas_select, "notas")
            self.__df_notas = self.__df_notas[self.__notas_select]
            self.__df_notas = self.__df_notas[self.__df_notas["cod_programa_estudiante"]==self.__programa]
            self.__df_nrcs = self.__df_notas.drop_duplicates(subset='NRC').reset_index(drop=True)

            self.__df_szascn = self._read_csv(self.__szascn_path)
            self._require_columns(self.__df_szascn, self.__szascn_select, "szascn")

            self.__df_nrcs_sin_seguimiento = self.__df_nrcs[
                ~self.__df_nrcs['NRC'].isin(self.__df_szascn['NRC'])
            ]

            self.__df_nrcs_con_seguimiento = self.__df_nrcs[
                self.__df_nrcs['NRC'].isin(self.__df_szascn['NRC'])
            ]

            self.__df_szascn_carrera = self.__df_szascn[
                self.__df_szascn['NRC'].isin(self.__df_nrcs_con_seguimiento['NRC'])
            ]

            programa_norm = str(self.__programa).strip().upper()
            rda_norm = (
                self.__df_szascn_carrera['RESULTADO DE APRENDIZAJE DEL PROGRAMA']
                .astype(str)
                .str.strip()
                .str.upper()
            )

            self.__df_szascn_otros_programas = self.__df_szascn_carrera[
                ~rda_norm.str.startswith(programa_norm)
            ]

            self.__df_szascn_del_programa = self.__df_szascn_carrera[
                rda_norm.str.startswith(programa_norm)
            ]

            # Resultados finales
            self.__df_no_registradas = self.__df_nrcs_sin_seguimiento.copy()
            self.__df_registradas_otro_programa = self.__df_szascn_otros_programas.copy()
            self.__df_registradas_programa = self.__df_szascn_del_programa.copy()

            programados = int(len(self.__df_nrcs))
            ejecutados = int(len(self.__df_nrcs_con_seguimiento))
            porcentaje = round((ejecutados / programados) * 100, 2) if programados > 0 else 0.0
            self.__cumplimiento = {
                "programados": programados,
                "ejecutados": ejecutados,
                "cumplimiento_pct": porcentaje,
                "rda_satisfaccion_media_pct": None,
                "docente_satisfaccion_media_pct": None,
                "satisfaccion_ordinal_media": None,
            }

            if debug == True:
                print("load_data:")
                print(f"- notas filas: {len(self.__df_notas)}")
                print(f"- nrcs unicos: {len(self.__df_nrcs)}")
                print(f"- szascn filas: {len(self.__df_szascn)}")
                print(f"- nrcs sin seguimiento: {len(self.__df_nrcs_sin_seguimiento)}")
                print(f"- nrcs con seguimiento: {len(self.__df_nrcs_con_seguimiento)}")
                print(f"- szascn carrera: {len(self.__df_szascn_carrera)}")
                print(f"- szascn del programa: {len(self.__df_szascn_del_programa)}")
                print(f"- szascn otros programas: {len(self.__df_szascn_otros_programas)}")
                print(f"- programados: {programados}")
                print(f"- ejecutados: {ejecutados}")
                print(f"- cumplimiento (%): {porcentaje}")

            if show == True:
                if not self.__df_nrcs.empty:
                    display(self.__df_nrcs.sample(min(2, len(self.__df_nrcs))))
                if not self.__df_szascn.empty:
                    display(self.__df_szascn.sample(min(2, len(self.__df_szascn))))

        except FileNotFoundError:
            raise FileNotFoundError(
                f"No se encontró uno de los archivos:\n"
                f"- notas: {self.__notas_path}\n"
                f"- szascn: {self.__szascn_path}\n"
                "Asegúrese de que las rutas existan."
            )

        except Exception as e:
            raise RuntimeError(
                "No se pudo cargar/procesar los archivos de Syllabus.\n"
                f"Detalle: {e}"
            )


    def prepare_data(self, show=False, debug=False):
        if self.__df_szascn_del_programa is None:
            raise RuntimeError("Ejecuta load_data() antes de prepare_data().")
        self.__df_szascn_filtered = self.__df_szascn_del_programa[self.__szascn_select].copy()

        self.__df_szascn_filtered['SEGUNDO NOMBRE DOCENTE'] = \
            self.__df_szascn_filtered['SEGUNDO NOMBRE DOCENTE'].fillna('')

        self.__df_szascn_filtered['Docente'] = (
            self.__df_szascn_filtered['APELLIDO DOCENTE'] + ' ' +
            self.__df_szascn_filtered['PRIMER NOMBRE DOCENTE'] + ' ' +
            self.__df_szascn_filtered['SEGUNDO NOMBRE DOCENTE']
        )

        self.__df_evaluaciones = self.__df_szascn_filtered[
            [
                'PERIODO', 'NRC', 'TITULO ASIGNATURA',
                'RESULTADO DE APRENDIZAJE DEL PROGRAMA',
                'ID DOCENTE', 'GRADO DE SATISFACIÓN',
                'Docente'
            ]
        ].copy()

        self.__df_evaluaciones.columns = [
            'Periodo', 'NRC', 'Materia',
            'RDA', 'Id_Docente', 'Satisfacción',
            'Docente'
        ]

        self.__df_evaluaciones['Label'] = (
            self.__df_evaluaciones['Docente']
            .str.replace('/', ' ', regex=True)
            .str.title()
        )

        encontrado = not self.__df_evaluaciones.empty
        if not encontrado and debug == True:
            print(
                "prepare_data: no hay evaluaciones para el programa solicitado. "
                "Se devolverán dataframes vacíos."
            )

        # Medias de satisfacción (alineadas con la lógica de gráficos)
        niveles = [
            "Nada Satisfactorio",
            "Poco Satisfactorio",
            "Medianamente Satisfactorio",
            "Satisfactorio",
            "Muy Satisfactorio",
        ]

        conteo_rda = (
            pd.crosstab(
                self.__df_evaluaciones["RDA"],
                self.__df_evaluaciones["Satisfacción"],
                normalize="index",
            )
            * 100
        ).reindex(columns=niveles, fill_value=0)
        conteo_rda["%Satisfechos"] = conteo_rda["Satisfactorio"] + conteo_rda["Muy Satisfactorio"]
        rda_media = round(float(conteo_rda["%Satisfechos"].mean()), 2) if not conteo_rda.empty else None

        conteo_doc = (
            pd.crosstab(
                self.__df_evaluaciones["Id_Docente"],
                self.__df_evaluaciones["Satisfacción"],
                normalize="index",
            )
            * 100
        ).reindex(columns=niveles, fill_value=0)
        conteo_doc["%Satisfechos"] = conteo_doc["Satisfactorio"] + conteo_doc["Muy Satisfactorio"]
        docente_media = round(float(conteo_doc["%Satisfechos"].mean()), 2) if not conteo_doc.empty else None

        escala = {
            "Nada Satisfactorio": 1,
            "Poco Satisfactorio": 2,
            "Medianamente Satisfactorio": 3,
            "Satisfactorio": 4,
            "Muy Satisfactorio": 5,
        }
        ordinal_series = self.__df_evaluaciones["Satisfacción"].map(escala).dropna()
        ordinal_media = round(float(ordinal_series.mean()), 2) if not ordinal_series.empty else None

        if self.__cumplimiento is None:
            self.__cumplimiento = {}
        self.__cumplimiento["rda_satisfaccion_media_pct"] = rda_media
        self.__cumplimiento["docente_satisfaccion_media_pct"] = docente_media
        self.__cumplimiento["satisfaccion_ordinal_media"] = (
            100 * ordinal_media / 5 if ordinal_media is not None else None
        )

        if debug == True:
            print("prepare_data:")
            print(f"- evaluaciones filas: {len(self.__df_evaluaciones)}")
            print(f"- media satisfaccion RDA (%): {rda_media}")
            print(f"- media satisfaccion Docente (%): {docente_media}")
            print(f"- satisfaccion ordinal media (1-5): {ordinal_media}")

        if show == True:
            display(self.__df_evaluaciones.sample(min(2, len(self.__df_evaluaciones))))

        return {
            "encontrado": encontrado,
            "evaluaciones": self.__df_evaluaciones.copy(),
            "szascn_filtrado": self.__df_szascn_filtered.copy(),
            "registradas_programa": self.__df_registradas_programa.copy() if self.__df_registradas_programa is not None else pd.DataFrame(),
            "registradas_otro_programa": self.__df_registradas_otro_programa.copy() if self.__df_registradas_otro_programa is not None else pd.DataFrame(),
            "no_registradas": self.__df_no_registradas.copy() if self.__df_no_registradas is not None else pd.DataFrame(),
        }

    def plot_valoracion_rdas(self, figname="valoracion_rda"):
        if self.__df_evaluaciones is None:
            raise RuntimeError("Primero ejecuta prepare_data() antes de graficar.")

        save_path = self._image_path / f"{figname}.png"

        conteo = (
            pd.crosstab(
                self.__df_evaluaciones["RDA"],
                self.__df_evaluaciones["Satisfacción"],
                normalize="index",
            )
            * 100
        )

        niveles = [
            "Nada Satisfactorio",
            "Poco Satisfactorio",
            "Medianamente Satisfactorio",
            "Satisfactorio",
            "Muy Satisfactorio",
        ]

        conteo = conteo.reindex(columns=niveles, fill_value=0)
        conteo["%Satisfechos"] = conteo["Satisfactorio"] + conteo["Muy Satisfactorio"]

        colores = ["#FD000099", "#FFAC7099", "#F4F42299", "#1452DD99", "#55C86899"]

        ax = conteo[niveles].plot(kind="bar", stacked=True, figsize=(12, 8), color=colores)

        for i, rda in enumerate(conteo.index):
            acumulado = 0
            for nivel in niveles:
                valor = float(conteo.loc[rda, nivel])
                if valor > 0:
                    ax.text(
                        i,
                        acumulado + valor / 2,
                        f"{valor:.1f}",
                        ha="center",
                        va="center",
                        color="black",
                        fontsize=8,
                    )
                acumulado += valor

        ax.plot(
            range(len(conteo.index)),
            conteo["%Satisfechos"],
            color="gray",
            marker="o",
            linewidth=2,
            label="% Satisfechos",
        )

        for i, val in enumerate(conteo["%Satisfechos"].values):
            ax.text(i, val + 2, f"{val:.1f}%", ha="center", color="gray", fontsize=9)

        plt.ylabel("Porcentaje (%) de Satisfacción")
        plt.xlabel("Resultado de Aprendizaje (RDA)")
        plt.legend(title="Satisfacción", loc="upper center")
        plt.ylim(0, 125)
        plt.xticks(rotation=90)
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        plt.show()

        print(f"Promedio General de Satisfacción: {conteo['%Satisfechos'].mean():.2f}%")

        return save_path

    def plot_valoracion_docente(self, figname="valoracion_docente"):
        if self.__df_evaluaciones is None:
            raise RuntimeError("Primero ejecuta prepare_data() antes de graficar.")

        save_path = self._image_path / f"{figname}.png"

        mapa_docentes = (
            self.__df_evaluaciones[["Id_Docente", "Docente"]]
            .dropna()
            .drop_duplicates()
        )

        conteo_doc = (
            pd.crosstab(
                self.__df_evaluaciones["Id_Docente"],
                self.__df_evaluaciones["Satisfacción"],
                normalize="index",
            )
            * 100
        )

        niveles = [
            "Nada Satisfactorio",
            "Poco Satisfactorio",
            "Medianamente Satisfactorio",
            "Satisfactorio",
            "Muy Satisfactorio",
        ]
        conteo_doc = conteo_doc.reindex(columns=niveles, fill_value=0)

        conteo_doc["%Insatisfechos"] = conteo_doc["Nada Satisfactorio"] + conteo_doc["Poco Satisfactorio"]
        conteo_doc["%Medianamente"] = conteo_doc["Medianamente Satisfactorio"]
        conteo_doc["%Satisfechos"] = conteo_doc["Satisfactorio"] + conteo_doc["Muy Satisfactorio"]

        conteo_doc = conteo_doc[["%Insatisfechos", "%Medianamente", "%Satisfechos"]].reset_index()
        conteo_doc = conteo_doc.merge(mapa_docentes, on="Id_Docente", how="left")

        conteo_doc["Etiqueta"] = conteo_doc["Docente"].astype(str).str.split().str[0]
        conteo_doc = conteo_doc.sort_values("%Satisfechos", ascending=False).reset_index(drop=True)

        ax = (
            conteo_doc.set_index("Etiqueta")[["%Insatisfechos", "%Medianamente", "%Satisfechos"]]
            .plot(
                kind="bar",
                stacked=True,
                figsize=(12, 8),
                color=["#FF6F61", "#F4F42299", "#55C86899"],
            )
        )

        plt.axhline(75, color="blue", linestyle="--", linewidth=2, label="Meta 75%")

        ax.plot(
            range(len(conteo_doc)),
            conteo_doc["%Satisfechos"].values,
            color="gray",
            marker="o",
            linewidth=2,
            label="% Satisfechos",
        )

        for i, val in enumerate(conteo_doc["%Satisfechos"].values):
            ax.text(i, val + 2, f"{val:.1f}%", ha="center", va="bottom", color="gray", fontsize=8)

        for i, row in conteo_doc.iterrows():
            insat = float(row["%Insatisfechos"])
            med = float(row["%Medianamente"])
            sat = float(row["%Satisfechos"])

            if insat > 0:
                ax.text(i, insat / 2, f"{insat:.1f}%", ha="center", va="center", color="white", fontsize=8)
            if med > 0:
                ax.text(i, insat + med / 2, f"{med:.1f}%", ha="center", va="center", color="black", fontsize=8)
            if sat > 0:
                ax.text(i, insat + med + sat / 2, f"{sat:.1f}%", ha="center", va="center", color="black", fontsize=8)

        plt.ylabel("Porcentaje (%)")
        plt.xlabel("Docente")
        plt.title("")
        plt.xticks(rotation=0, ha="center")
        plt.ylim(0, 120)
        plt.legend(title="Nivel de satisfacción")
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        plt.show()

        return save_path

    # ----------------------------
    # Getters (salidas solicitadas)
    # ----------------------------
    def get_materias_no_registradas(self):
        if self.__df_no_registradas is None:
            raise RuntimeError("Ejecuta load_data() y prepare_data() antes de pedir los dataframes.")
        if self.__df_no_registradas.empty:
            df_table = self.__df_no_registradas.copy()
        else:
            df_table = self.__df_no_registradas.rename(
                columns={
                    "NRC": "NRC",
                    "NIVEL": "Nivel",
                    "titulo_curso": "Materia",
                    "cod_programa_estudiante": "Programa",
                }
            )[
                ["NRC", "Nivel", "Materia", "Programa"]
            ]
        self._write_table(
            df_table,
            table_name="syllabus_materias_no_registradas",
            caption="Materias no registradas",
            label="syllabus_materias_no_registradas",
        )
        return self.__df_no_registradas.copy()

    def get_materias_registradas_otro_programa(self):
        if self.__df_registradas_otro_programa is None:
            raise RuntimeError("Ejecuta load_data() y prepare_data() antes de pedir los dataframes.")
        if self.__df_registradas_otro_programa.empty:
            df_table = self.__df_registradas_otro_programa.copy()
        else:
            df_table = self.__df_registradas_otro_programa.copy()
            df_table["Docente"] = (
                df_table["APELLIDO DOCENTE"].astype(str).fillna("").str.strip()
                + " "
                + df_table["PRIMER NOMBRE DOCENTE"].astype(str).fillna("").str.strip()
                + " "
                + df_table["SEGUNDO NOMBRE DOCENTE"].astype(str).fillna("").str.strip()
            ).str.replace(r"\s+", " ", regex=True).str.strip()
            df_table["Docente"] = df_table["Docente"].apply(self.text_title_case)
            df_table = df_table.rename(
                columns={
                    "PERIODO": "Periodo",
                    "NRC": "NRC",
                    "TITULO ASIGNATURA": "Materia",
                    "RESULTADO DE APRENDIZAJE DEL PROGRAMA": "RdA",
                }
            )[
                ["Periodo", "NRC", "Materia", "RdA", "Docente"]
            ]
        self._write_table(
            df_table,
            table_name="syllabus_materias_registradas_otro_programa",
            caption="Materias registradas en otro programa",
            label="syllabus_materias_registradas_otro_programa",
        )
        return self.__df_registradas_otro_programa.copy()

    def get_materias_registradas_programa(self):
        if self.__df_registradas_programa is None:
            raise RuntimeError("Ejecuta load_data() y prepare_data() antes de pedir los dataframes.")
        if self.__df_registradas_programa.empty:
            df_table = self.__df_registradas_programa.copy()
        else:
            df_table = self.__df_registradas_programa.copy()
            df_table["Docente"] = (
                df_table["APELLIDO DOCENTE"].astype(str).fillna("").str.strip()
                + " "
                + df_table["PRIMER NOMBRE DOCENTE"].astype(str).fillna("").str.strip()
                + " "
                + df_table["SEGUNDO NOMBRE DOCENTE"].astype(str).fillna("").str.strip()
            ).str.replace(r"\s+", " ", regex=True).str.strip()
            df_table["Docente"] = df_table["Docente"].apply(self.text_title_case)
            df_table = df_table.rename(
                columns={
                    "PERIODO": "Periodo",
                    "NRC": "NRC",
                    "TITULO ASIGNATURA": "Materia",
                    "RESULTADO DE APRENDIZAJE DEL PROGRAMA": "RdA",
                }
            )[
                ["Periodo", "NRC", "Materia", "RdA", "Docente"]
            ]
        self._write_table(
            df_table,
            table_name="syllabus_materias_registradas_programa",
            caption="Materias registradas del programa",
            label="syllabus_materias_registradas_programa",
        )
        return self.__df_registradas_programa.copy()

    def get_cumplimiento(self):
        if self.__cumplimiento is None:
            raise RuntimeError("Ejecuta load_data() antes de pedir el cumplimiento.")
        return self.__cumplimiento.copy()

    # ----------------------------
    # Runner (produce TODO: 2 gráficos + 2 dataframes finales)
    # ----------------------------
    def run_outputs(self, show=False, debug=False, rda_fig="valoracion_rda", docente_fig="valoracion_docente"):
        """
        Ejecuta el pipeline completo y devuelve:
          - paths de 2 gráficos (RDA y Docente)
          - 2 dataframes finales: (registradas_otros_programas, registradas_programa)
        """
        if self.__df_szascn is None or self.__df_notas is None:
            self.load_data(show=show, debug=debug)
        elif debug == True:
            print("run_outputs: usando datos cargados")

        if self.__df_evaluaciones is None:
            prep = self.prepare_data(show=show, debug=debug)
        else:
            prep = {"encontrado": not self.__df_evaluaciones.empty}
            if debug == True:
                print("run_outputs: usando datos preparados")

        omitio_graficos = False
        if not prep.get("encontrado", True):
            if debug == True:
                print("run_outputs: sin datos para gráficos, se omiten.")
            rda_path = None
            docente_path = None
            omitio_graficos = True
        else:
            rda_path = self.plot_valoracion_rdas(figname=rda_fig)
            docente_path = self.plot_valoracion_docente(figname=docente_fig)

        otros_programas = self.get_materias_registradas_otro_programa()
        programa = self.get_materias_registradas_programa()
        no_ejecuta=self.get_materias_no_registradas()
        cumplimiento = self.get_cumplimiento()

        return {
            "fig_rda": rda_path,
            "fig_docente": docente_path,
            "otro_programa": otros_programas,
            "programa": programa,
            "no_registradas":no_ejecuta,
            "cumplimiento": cumplimiento,
            "graficos_omitidos": omitio_graficos,
            "encontrado": prep.get("encontrado", True)
        }


class SyllabusControl(Syllabus):
    def __init__(
        self,
        periodo,
        programa=None,
        calificaciones_path=None,
        szascap_path=None,
        image_path="../Latex/Contenido/images/",
    ):
        super().__init__(periodo, titulo="Informe de Control de Sílabos", image_path=image_path)

        if calificaciones_path is None:
            calificaciones_path = f"./assets/Calificaciones{periodo}.csv"
        if szascap_path is None:
            szascap_path = "./assets/szascap.csv"

        self.__programa = programa
        self.__calificaciones_path = calificaciones_path
        self.__szascap_path = szascap_path

        self.__calificaciones_select = ["NRC", "nombres_completos_docente", "titulo_curso", "NIVEL"]
        self.__szascap_select = ["NRC", "ESTADO"]

        self.__df_nrcs = None
        self.__df_szascap = None
        self.__df_final = None

    def load_data(self, show=False, debug=False):
        try:
            self.__df_nrcs = self._read_csv(self.__calificaciones_path)
            select_cols = list(self.__calificaciones_select)
            if self.__programa is not None:
                select_cols.append("cod_programa_estudiante")
            self._require_columns(self.__df_nrcs, select_cols, "calificaciones")
            self.__df_nrcs = self.__df_nrcs[select_cols]
            if self.__programa is not None:
                self.__df_nrcs = self.__df_nrcs[self.__df_nrcs["cod_programa_estudiante"] == self.__programa]
            self.__df_nrcs = (
                self.__df_nrcs[self.__calificaciones_select]
                .drop_duplicates("NRC")
                .sort_values("NIVEL")
                .reset_index(drop=True)
            )
            self.__df_nrcs = self.df_title_case(self.__df_nrcs)

            self.__df_szascap = self._read_csv(self.__szascap_path)
            self._require_columns(self.__df_szascap, self.__szascap_select, "szascap")
            self.__df_szascap = self.__df_szascap[self.__szascap_select]
            self.__df_szascap = self.df_title_case(self.__df_szascap)

            if debug == True:
                print("load_data (control):")
                print(f"- nrcs filas: {len(self.__df_nrcs)}")
                print(f"- szascap filas: {len(self.__df_szascap)}")

            if show == True:
                if not self.__df_nrcs.empty:
                    display(self.__df_nrcs.sample(min(2, len(self.__df_nrcs))))
                if not self.__df_szascap.empty:
                    display(self.__df_szascap.sample(min(2, len(self.__df_szascap))))

        except FileNotFoundError:
            raise FileNotFoundError(
                f"No se encontró uno de los archivos:\n"
                f"- calificaciones: {self.__calificaciones_path}\n"
                f"- szascap: {self.__szascap_path}\n"
                "Asegúrese de que las rutas existan."
            )

        except Exception as e:
            raise RuntimeError(
                "No se pudo cargar/procesar los archivos de Control de Sílabos.\n"
                f"Detalle: {e}"
            )

    def prepare_data(self, show=False, debug=False):
        if self.__df_nrcs is None or self.__df_szascap is None:
            raise RuntimeError("Ejecuta load_data() antes de prepare_data().")

        self.__df_final = self.__df_nrcs.merge(self.__df_szascap, on="NRC", how="left")
        self.__df_final.columns = ["NRC", "Docente", "Asignatura", "Nivel", "Observación"]
        self.__df_final = self.__df_final.drop_duplicates("NRC").fillna("ND")

        encontrado = not self.__df_final.empty
        if not encontrado and debug == True:
            print("prepare_data (control): no hay datos, se devolverán dataframes vacíos.")

        if debug == True:
            print("prepare_data (control):")
            print(f"- filas: {len(self.__df_final)}")

        if show == True and not self.__df_final.empty:
            display(self.__df_final.sample(min(2, len(self.__df_final))))

        return {
            "encontrado": encontrado,
            "resultados": self.__df_final.copy(),
        }

    def _control_table_to_latex(self, df, caption, label):
        if df is None or df.empty:
            df = pd.DataFrame(
                [
                    {
                        "NRC": "",
                        "Docente": "",
                        "Asignatura": "",
                        "Nivel": "",
                        "Observación": "No se encontraron datos.",
                    }
                ]
            )

        latex = r"""
\begin{longtblr}[
  caption={""" + caption + r"""},
]{
  colspec={
    Q[c,m,0.8cm]   % N°
    Q[l,m,1.5cm]   % NRC
    Q[l,m,3.5cm]   % Docente
    Q[l,m,4cm]     % Asignatura
    Q[c,m,1cm]     % Nivel
    Q[l,m,2.5cm]   % Observación
  },
  row{1-Z} = {font=\footnotesize},
  row{1} = {bg=colhead!40, font=\footnotesize \bfseries},
  hlines,
  vlines
}
N° & NRC & Docente & Asignatura & Nivel & Observación \\
"""

        for i, row in df.reset_index(drop=True).iterrows():
            num = i + 1
            nrc = row.get("NRC", "")
            docente = row.get("Docente", "")
            asignatura = row.get("Asignatura", "")
            nivel = row.get("Nivel", "")
            obs = "" if pd.isna(row.get("Observación", "")) else row.get("Observación", "")

            latex += f"{num} & {nrc} & {docente} & {asignatura} & {nivel} & {obs} \\\\\n"

        latex += r"\end{longtblr}"

        return latex.strip()

    def get_resultados(self, table_name="control_silabos_resultados"):
        if self.__df_final is None:
            raise RuntimeError("Ejecuta load_data() y prepare_data() antes de pedir los dataframes.")

        self._tables_dir.mkdir(parents=True, exist_ok=True)
        table = self._control_table_to_latex(
            self.__df_final,
            caption="Matriz de resultados del control de sílabos de la carrera de \\carrera",
            label="control_silabos_resultados",
        )

        table_file = self._tables_dir / f"{table_name}.tex"
        with open(table_file, "w", encoding="utf-8") as f:
            f.write(table)

        return self.__df_final.copy()

    def plot_resultados(self, figname="resultados"):
        if self.__df_final is None:
            raise RuntimeError("Primero ejecuta prepare_data() antes de graficar.")

        if self.__df_final.empty:
            return None

        save_path = self._image_path / f"{figname}.png"

        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        if sns is not None:
            sns.countplot(data=self.__df_final, x="Observación", ax=ax, hue="Observación", palette="Set3")
        else:
            counts = self.__df_final["Observación"].value_counts()
            counts.plot(kind="bar", ax=ax, color="#8FB9A8")

        for p in ax.patches:
            altura = p.get_height()
            if altura is None:
                continue
            ax.annotate(
                f"{int(altura)}",
                (p.get_x() + p.get_width() / 2, altura),
                ha="center",
                va="bottom",
                fontsize=12,
            )

        ax.set_xlabel("Observación")
        ax.set_ylabel("Cantidad")
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        plt.show()

        return save_path

    def run_outputs(self, show=False, debug=False, resultados_fig="resultados"):
        if self.__df_nrcs is None or self.__df_szascap is None:
            self.load_data(show=show, debug=debug)
        elif debug == True:
            print("run_outputs (control): usando datos cargados")

        if self.__df_final is None:
            prep = self.prepare_data(show=show, debug=debug)
        else:
            prep = {"encontrado": not self.__df_final.empty}
            if debug == True:
                print("run_outputs (control): usando datos preparados")

        omitio_graficos = False
        if not prep.get("encontrado", True):
            if debug == True:
                print("run_outputs (control): sin datos para gráficos, se omiten.")
            fig_path = None
            omitio_graficos = True
        else:
            fig_path = self.plot_resultados(figname=resultados_fig)

        resultados = self.get_resultados()

        return {
            "fig_resultados": fig_path,
            "resultados": resultados,
            "graficos_omitidos": omitio_graficos,
            "encontrado": prep.get("encontrado", True),
        }
