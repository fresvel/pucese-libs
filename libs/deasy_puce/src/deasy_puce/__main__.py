from .informe.informe import Informe
from .latex.tblr import LatexTblr
from .horario.horario import Horario

def main():
    print("Informes Pucese!")
    informe=Informe("202661")
    print(informe.version)
    print(informe._periodo)
    longtblr=LatexTblr()
    print(longtblr.header_color)
    horario=Horario("202661")
    print(horario.data_path)
    print(horario._semestre)

