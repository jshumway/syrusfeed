

def human_date(date):
    return date.strftime("%d %B %Y")

def export_filters():
    return {'humandate': human_date}
