from flask import Flask, render_template, request, json
import requests
import pandas as pd

PRED_MODEL = '../../../prediction_ranked_Wiki2PropDEPLOY_year2018_embedding300LG_DEPLOY.h5'

app = Flask(__name__)

def query_property_labels(properties, lang="en"):
    query = '''SELECT ?p ?pLabel WHERE {
  VALUES ?p { %s }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],%s". }
}''' % (" ".join(map(lambda p: 'wd:'+p, properties)), lang)

    url = 'https://query.wikidata.org/bigdata/namespace/wdq/sparql'
    data = requests.get(url, params={'query': query, 'format': 'json'}).json()
    response = {} 
    for P in data['results']['bindings']:
        response[P['p']['value'][31:]] = (P['pLabel']['value'])
    return response

def query_properties(subject):
    query = '''SELECT DISTINCT ?p {
  wd:Q%s ?p ?statement .
  ?wd wikibase:claim ?p.
}''' % subject

    url = 'https://query.wikidata.org/bigdata/namespace/wdq/sparql'
    data = requests.get(url, params={'query': query, 'format': 'json'}).json()
    response = []
    for P in data['results']['bindings']:
        response.append(P['p']['value'][29:])
    return response
    

@app.route('/')
def get_missing_attributes():


    #handle n parameter
    n = request.args.get('n')
    if n:
        try:
            n=int(n)
        except:
            return render_template("404.html", error='N is not a valid integer.'), 404
    else:
        n = 10


    #handle subject parameter
    subject = request.args.get('subject')

    if subject:
        try:
            subject=str(int(subject[1:]))
        except:
            return render_template("404.html", error='Subject is not a valid Entity in the form "Q42".'), 404

        response = { "subject": "Q"+subject, "missing_properties" : [] }

        prediction = pd.read_hdf(PRED_MODEL,'df',where='index='+subject)
        if prediction.shape[0]:
            existing = query_properties(subject)
            for P in prediction[prediction.columns.difference(existing)].sort_values(by=prediction.index[0] , axis=1, ascending=False).iloc[:,0:n]:
                response['missing_properties'].append( {
                    "property": P,
                    "predicted": "{:.2%}".format(prediction.iloc[0][P])
                    } )
        else:
            return render_template("404.html", error='Entity not found in index.'), 404
    else:
        return render_template("index.html")


    #handle lang parameter
    lang = request.args.get('lang')
    if not lang:
        lang = 'en'

    property_labels = query_property_labels(map(lambda p: p["property"], response['missing_properties']), lang=lang)

    for p in response['missing_properties']:
        p['label'] = property_labels[p['property']]
   
    callback = request.args.get('callback', False)
    if callback:
        return str(callback) + '(' + json.dumps(response, indent=4)+ ')' , 200, {'content-type':'application/javascript'}

    if request.accept_mimetypes.find('text/html') != -1:
        return render_template("index.html", content=response)
    else:
      	return json.dumps(response, indent=4), 200, {'content-type':'application/json'}
