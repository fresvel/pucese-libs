from .informe.informe import Informe
from .latex.tblr import LatexTblr
from .horario.horario import Horario
from .syllabus.syllabus import SyllabusSeguimiento, SyllabusControl

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
    seguimiento=SyllabusSeguimiento("202566", "E055", "r1", "r2")
    control=SyllabusControl("202566", "E055", "r1", "r2")
    print(seguimiento._semestre)
    print(control._semestre)
