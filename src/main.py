import requests
import pandas as pd
import zipfile
import io
import json
from datetime import datetime, timedelta
from jinja2 import Environment, FileSystemLoader
from utils import workflow
from email_client import EmailSender
from io import BytesIO
import argparse
import os


def vulnexport(last_days, include_news, title_customization, time_customization):
    data = requests.get(
        'https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json').json()

    df = pd.DataFrame(data['vulnerabilities'])
    # parse the dateAdded column as datetime
    df['dateAdded'] = pd.to_datetime(df['dateAdded'])
    # create html table with cveID, vendorProject, product, vulnerabilityName, dateAdded, shortDescription, requiredAction
    current_date = datetime.now()

    news = workflow(last_days)

    news = pd.DataFrame(
        news, columns=['cveID', 'vulnerabilityName', 'shortDescription', 'url'])
    news = news.explode('cveID')
    news = news.drop_duplicates(subset='cveID', keep='first')

    news = news[~news['cveID'].isin(df['cveID'])]

    # export news to csv

    from_date = current_date - timedelta(days=last_days)

    df = df[(df['dateAdded'] >= from_date)
            & (df['dateAdded'] <= current_date)]

    df['isNews'] = False
    news['isNews'] = True

    df = pd.concat([news, df], ignore_index=True)

    def download_and_extract_json(url):
        # Download the zip file into a BytesIO buffer
        print("Downloading zip file...")
        response = requests.get(url)
        zip_buffer = io.BytesIO(response.content)

        # Extract the zip file from the buffer
        print("Extracting zip file...")
        with zipfile.ZipFile(zip_buffer, 'r') as zip_ref:
            # Find the JSON file inside the zip
            json_filename = None
            for file in zip_ref.namelist():
                if file.endswith('.json'):
                    json_filename = file
                    break

            # Load the JSON data from the file in the zip
            if json_filename:
                with zip_ref.open(json_filename) as json_file:
                    print("Loading JSON data...")
                    data = json.load(json_file)
                return data
            else:
                raise FileNotFoundError(
                    "No JSON file found in the extracted contents.")

    url = 'https://nvd.nist.gov/feeds/json/cve/1.1/nvdcve-1.1-recent.json.zip'

    enrichments = download_and_extract_json(url)
    enrichment = [{'cveID': "dummy", 'severity': "dummy"}]

    colors = {'CRITICAL': 'darkred', 'HIGH': 'red',
              'MEDIUM': 'orange', 'LOW': 'green'}
    for vuln in enrichments.get('CVE_Items', []):
        aux = {'cveID': vuln['cve']['CVE_data_meta']['ID'],
               'publishedDate': vuln['publishedDate']}
        if vuln['impact'] != {}:
            aux['severity'] = vuln['impact']['baseMetricV3']['cvssV3']['baseSeverity']
            aux['color'] = colors[aux['severity']]
        enrichment.append(aux)

    enrichment_df = pd.DataFrame(enrichment)
    enrichment_df['publishedDate'] = pd.to_datetime(
        enrichment_df['publishedDate']).dt.tz_localize(None)

    filterTime = current_date - timedelta(days=30)

    df = df.join(enrichment_df.set_index('cveID'), on='cveID', how='left')

    df = df[(df['publishedDate'] >= filterTime) | (df['isNews'] == True)]

    df['severity'] = df['severity'].fillna('Pending NIST severity assessment')
    df['product'] = df['product'].fillna('Pending CISA KEV assessment')
    df['requiredAction'] = df['requiredAction'].fillna(
        'Pending CISA KEV assessment')
    df['color'] = df['color'].fillna('cornflowerblue')
    df['url'] = df['url'].fillna(
        'https://nvd.nist.gov/vuln/detail/' + df['cveID'])

    df.fillna('', inplace=True)

    columnName = "Vulnerability Name"
    news = df.rename(
        columns={'vulnerabilityName': 'Vulnerability Name / News Title'})

    if include_news:
        columnName = "Vulnerability Name / News Title"
    else:
        df = df[df['isNews'] == False]

    data = {"fromDate": from_date.strftime(
        '%d/%m/%Y'), "toDate": current_date.strftime('%d/%m/%Y'), "cves": df.to_dict(orient='records'), "columnName": columnName, "title_customization": title_customization, "time_customization": time_customization}

    if df.empty:
        data["noFinding"] = "After conducting a detailed evaluation, our team did not detect any security vulnerabilities or potential risks within the specified timeframe."
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env = Environment(loader=FileSystemLoader(script_dir))
    template = env.get_template('template.html')

    return template.render(data), news


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Generate vulnerability reports")
    parser.add_argument(
        '--report-type',
        choices=['0day', 'weekly'],
        default='0day',
        required=False,
        help="Type of report to generate: '0day' for 0 day report, 'weekly' for weekly report"
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_arguments()
    if args.report_type == '0day':
        output, news = vulnexport(1, True, "Daily", "today")
    else:
        output, news = vulnexport(7, True, "Weekly", "this week")
    # with open('output.html', 'w') as f:
    #     f.write(output)
    # news.to_excel('news.xlsx', index=False)
    excel_buffer = BytesIO()
    news.to_excel(excel_buffer, index=False, engine='openpyxl')
    excel_buffer.seek(0)  # Rewind the buffer
    file = excel_buffer.read()

    from_email = 'es.soc.support@devoteam.com'
    to_day_emails = ['eric.guerra@devoteam.com',
                     'biel.camprubi@devoteam.com', 'alejandro.gonzalez1@devoteam.com']
    to_week_emails = ['es.soc.l2@devoteam.com', 'biel.camprubi@devoteam.com',
                      'alejandro.gonzalez1@devoteam.com', "dpuentep@cirsa.com",
                      "aesalgado@covisian.com",
                      "pedro.moral@konecta-group.com",
                      "sandra.medina@konecta-group.com",
                      "daniel.navas@konecta-group.com",
                      "ismael.rossell@roche.com",
                      "bernat.hosta@roche.com",
                      "ramiro.maicas@normon.com",
                      "jvicente@grupobc.com",
                      "darino@grupobc.com",
                      "Imanol.Garrido@aegps.com",
                      "mikel.garcia@venanpri.com",
                      "antonio.bernabe@paack.co",
                      "nicolas.francia@paack.co", "ivanzomenyo@bit2me.com", "damianrivera@bit2me.com", "mbfierro@konecta-group.com"
                      ]

    # with open('output.html', 'r') as f:
    #     output = f.read()
    sender = EmailSender('es.soc.support@devoteam.com', 'qpoigouijrltltbr')

    if args.report_type == '0day':
        sender.send_file_email(from_email,
                               to_day_emails, 'Devoteam 0 day Vulnerability Report', output, file, 'news.xlsx')

    else:
        sender.send_html_email(from_email,
                               to_week_emails, 'Devoteam Weekly CTI Report', output)
