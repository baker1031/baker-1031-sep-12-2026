import re
# British -> American. Proper nouns keep their spelling, so only lower-case forms are rewritten,
# except "Programme"/"Capitalisation"/"Amortisation"/"Organisation" which are never property names.
MAP = {
 'capitalisation':'capitalization','capitalise':'capitalize','capitalised':'capitalized','capitalising':'capitalizing',
 'programme':'program','programmes':'programs','totalling':'totaling','totalled':'totaled',
 'amortisation':'amortization','amortise':'amortize','amortised':'amortized','amortising':'amortizing',
 'catalogue':'catalog','catalogues':'catalogs','centre':'center','centres':'centers',
 'harbour':'harbor','harbours':'harbors','organisation':'organization','organisations':'organizations',
 'realise':'realize','realised':'realized','realising':'realizing','recognise':'recognize','recognised':'recognized',
 'modelled':'modeled','modelling':'modeling','collateralised':'collateralized','stabilised':'stabilized',
 'stabilising':'stabilizing','summarised':'summarized','internalise':'internalize','diarise':'calendar',
 'honour':'honor','honoured':'honored','honouring':'honoring','favour':'favor','favourable':'favorable',
 'favours':'favors','behaviour':'behavior','licence':'license','theatre':'theater','cheque':'check','cheques':'checks',
 'storey':'story','storeys':'stories','sizeable':'sizable','utilise':'utilize','utilised':'utilized',
 'analyse':'analyze','analysed':'analyzed','defence':'defense','offence':'offense','labelled':'labeled',
 'labelling':'labeling','travelled':'traveled','travelling':'traveling','fibre':'fiber',
}
_ALWAYS = {'programme','programmes','capitalisation','capitalise','capitalised','capitalising',
           'amortisation','amortise','amortised','amortising','organisation','organisations','totalling','totalled'}
_PAT = re.compile(r'\b(' + '|'.join(sorted(MAP, key=len, reverse=True)) + r')\b', re.I)

def americanise(text):
    if not isinstance(text, str):
        return text
    def sub(m):
        w = m.group(0); low = w.lower()
        if w[0].isupper() and low not in _ALWAYS:
            return w                      # a capitalised word here is almost always a property or firm name
        rep = MAP[low]
        return rep.capitalize() if w[0].isupper() else rep
    return _PAT.sub(sub, text)
