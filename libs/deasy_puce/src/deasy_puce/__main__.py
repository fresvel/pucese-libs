from .informe.informe import Informe
from .latex.tblr import LatexTblr
def main():
    print("Informes Pucese!")
    informe=Informe("202566")
    print(informe.version)
    print(informe._periodo)
    print(informe.text_title_case("HOLA MUNDO"))
    longtblr=LatexTblr()
    print(longtblr.header_color)