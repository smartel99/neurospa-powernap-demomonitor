from django.http import HttpResponse, HttpRequest
from django.template import loader
from background_task import background
import smtplib
import datetime
import time
import mongoengine

stations = {}


class DemoStation(mongoengine.Document):
    name = mongoengine.StringField()
    ip = mongoengine.StringField()
    address = mongoengine.StringField()
    last_seen = mongoengine.DateTimeField()
    is_alive = mongoengine.BooleanField()

    meta = {
        'db_alias': "core",
        'collection': "stations"
    }


@background(schedule=0)
def check_last_ping():
    is_init = False
    if not is_init:
        mongoengine.register_connection(alias="core", name="stations")
    for station in DemoStation.objects():
        # If station hasn't pinged for 15 minutes:
        d = datetime.datetime.now() - station.last_seen
        if d.seconds >= 900:
            if station.is_alive:
                submit(station)


# Create your views here.
def index(req: HttpRequest):
    is_init = False
    if not is_init:
        mongoengine.register_connection(alias="core", name="stations")
    print(req.POST)
    if req.method != "POST":
        return HttpResponse(loader.get_template("polls/forbidden.html").render({}, req))
    else:
        check_last_ping(repeat=1, repeat_until=None)
        station = DemoStation.objects(ip=req.POST.get("ip", "")).first()
        if station:
            station.last_seen = datetime.datetime.now()
            station.is_alive = True
            station.save()
        else:
            station = DemoStation()
            station.name = req.POST.get("name", "N/A")
            station.ip = req.POST.get("ip", "N/A")
            station.address = req.POST.get("notifyAddr", "")
            station.last_seen = datetime.datetime.now()
            station.is_alive = True
            station.save()

    return HttpResponse(loader.get_template("polls/forbidden.html").render({}, req))


def submit(station: DemoStation):
    if station.is_alive:
        station.is_alive = False
        station.save()
        print(f"Station {station.name} has not pinged for more than 15 minutes!")
        server = smtplib.SMTP_SSL("smtp.gmail.com", port=465)
        from_addr = "neurospa.demo.station@gmail.com"
        to_addr = [station.address]
        subject = "No response from NeuroSpa PowerNap demonstration station"
        txt = f"The NeuroSpa PowerNap demonstration station \"{station.name}\" ({station.ip}) has stopped responding.\n" \
              f"It was last hear on {station.last_seen} UTC."
        msg = """From: %s\r\nTo: %s\r\nSubject: %s\r\n\
            
%s
            """ % (from_addr, ", ".join(to_addr), subject, txt)
        server.login("neurospa.demo.station@gmail.com", "GssLab402")
        if station.address is not "":
            server.sendmail(from_addr, to_addr, msg)
        server.quit()
