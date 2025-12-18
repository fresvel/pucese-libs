import pandas as pd

from pathlib import Path



from deasy_puce import Informe

class Distributivo(Informe):
    def __init__(self, periodo, data_path):
        self.__titulo='DISTRIBUTIVO ACADÉMICO Y DE GESTIÓN'
        super().__init__(periodo, self.__titulo)
        self.data_path=data_path
        self.save_path='../Latex/Contenido/'
        

    def load_data(self):
        self.dataframe = pd.read_excel(self.data_path)
        self.dataframe = self.df_title_case(self.dataframe)
        carreras = pd.DataFrame(self.dataframe['Carrera'].dropna().unique(),columns=["Carrera"])
        display(carreras)
        index_carrera = int(input("Ingrese el número que corresponde a la carrera: "))
        self.carrera=carreras.iloc[index_carrera]["Carrera"]

    
    def __get_docentes(self):
        df_docentes=self.dataframe[self.dataframe['Carrera']==self.carrera].drop_duplicates('Cédula')
        docentes=df_docentes['Cédula']

        
        return docentes
        
    
    def build_tables(self):
        print("Building...")

        tables_dir = Path(self.save_path) / "tables"
        tables_dir.mkdir(parents=True, exist_ok=True)

        for file in tables_dir.glob("*.tex"):
            file.unlink()

        docentes = self.__get_docentes()

        content=''
        for index, docente in enumerate(docentes):
            df_table = self.dataframe[self.dataframe['Cédula'] == docente]
            df_table = df_table.fillna('-')

            print(docente)

            table = self.dataframe_to_latex(
                df_table,
                caption='',
                label='',
                set_caption='empty',
                scale=[2,3,1,1,3,1,1,1,1,2,2,2]
            )

            if table!="":
                table_file = tables_dir / f"table_{index}.tex"
                with open(table_file, "w", encoding="utf-8") as f:
                    f.write(table)

                content+="\\input{Contenido/tables/table_"+f"{index}.tex"+"}\n"
            
        content_file = tables_dir / ".."/"Content.tex"
        with open(content_file,"w", encoding="utf-8") as f:
                f.write(content)
        
        self.render_header_tex(self.carrera)


    def build_content(self):
        pass
        
