from bs4 import BeautifulSoup

soup = BeautifulSoup(open('data/tracker_test.html', encoding='utf-8'), 'html.parser')
form = soup.find('form', id='tr-form') or soup.find('form')

print("Form action:", form.get('action'))
print("Form method:", form.get('method'))

inputs = form.find_all(['input', 'select'])
for inp in inputs:
    name = inp.get('name')
    val = inp.get('value')
    inp_type = inp.get('type')
    if name:
        if inp.name == 'select':
            sel_opt = inp.find('option', selected=True)
            print(f"Select: {name} (selected: {sel_opt.get('value') if sel_opt else 'none'})")
        else:
            print(f"Input: {name} | type={inp_type} | value={val}")
