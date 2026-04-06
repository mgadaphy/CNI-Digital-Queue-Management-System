import sys
import os
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from app import create_app, socketio

def setup_database(app_instance):
    from app.extensions import db
    from app.models import Agent, ServiceType, SystemConfig, Station, Citizen, Queue

    with app_instance.app_context():
        print("Creating database tables...")
        db.create_all()

        # ── Admin ─────────────────────────────────────────────────────────────
        admin = Agent.query.filter_by(employee_id='ADMIN001').first()
        if not admin:
            print("Creating System Administrator (ADMIN001)...")
            admin = Agent(
                employee_id='ADMIN001',
                first_name='System',
                last_name='Administrator',
                email='admin@cni.gov',
                role='admin',
                is_active=True,
                status='available'
            )
            admin.set_password('admin123')
            db.session.add(admin)

        # ── 4 Agents ──────────────────────────────────────────────────────────
        agents_data = [
            ('AGT001', 'Marie',   'Kouassi', 'marie@cni.gov'),
            ('AGT002', 'Kofi',    'Asante',  'kofi@cni.gov'),
            ('AGT003', 'Ibrahim', 'Traore',  'ibrahim@cni.gov'),
            ('AGT004', 'Aminata', 'Diallo',  'aminata@cni.gov'),
        ]
        agents = []
        for emp_id, fname, lname, email in agents_data:
            agent = Agent.query.filter_by(employee_id=emp_id).first()
            if not agent:
                print(f"Creating Agent {emp_id} ({fname} {lname})...")
                agent = Agent(
                    employee_id=emp_id,
                    first_name=fname,
                    last_name=lname,
                    email=email,
                    role='agent',
                    is_active=True,
                    status='available'
                )
                agent.set_password('agent123')
                db.session.add(agent)
            agents.append(agent)
        db.session.flush()

        # ── Service Types ─────────────────────────────────────────────────────
        print("Initializing CNI Service Types...")
        services_data = [
            {'code': 'NEW_APP',    'name_fr': 'Nouvelle Demande', 'name_en': 'New Application', 'priority': 10, 'duration': 15},
            {'code': 'RENEWAL',    'name_fr': 'Renouvellement',   'name_en': 'Renewal',          'priority': 20, 'duration': 10},
            {'code': 'COLLECTION', 'name_fr': 'Retrait',          'name_en': 'Collection',       'priority': 30, 'duration': 5},
            {'code': 'CORRECTION', 'name_fr': 'Perte/Correction', 'name_en': 'Lost/Correction',  'priority': 40, 'duration': 20}
        ]
        db_services = {}
        for srv in services_data:
            service = ServiceType.query.filter_by(code=srv['code']).first()
            if not service:
                service = ServiceType(
                    code=srv['code'],
                    name_fr=srv['name_fr'],
                    name_en=srv['name_en'],
                    priority_level=srv['priority'],
                    estimated_duration=srv['duration'],
                    is_active=True
                )
                db.session.add(service)
                db.session.flush()
            db_services[srv['code']] = service

        # ── System Config ─────────────────────────────────────────────────────
        print("Configuring System Preferences...")
        if not SystemConfig.query.filter_by(key='auto_assign_enabled').first():
            db.session.add(SystemConfig(key='auto_assign_enabled', value='true'))

        # ── 4 Stations (one per agent) ────────────────────────────────────────
        print("Building Workstations (Counters)...")
        stations_data = [
            ('C01', 'Counter 1 (Fast Track)'),
            ('C02', 'Counter 2 (Standard)'),
            ('C03', 'Counter 3 (Standard)'),
            ('C04', 'Counter 4 (Special Needs)'),
        ]
        stations = []
        for number, name in stations_data:
            station = Station.query.filter_by(station_number=number).first()
            if not station:
                station = Station(station_number=number, name=name, status='available', is_active=True)
                db.session.add(station)
            stations.append(station)
        db.session.commit()

        # Assign each agent to their counter
        for agent, station in zip(agents, stations):
            if agent and not agent.current_station_id:
                agent.current_station_id = station.id
        db.session.commit()

        # ── 28 Sample Citizens ────────────────────────────────────────────────
        citizens_list = []
        if Citizen.query.count() == 0:
            print("Registering Sample Citizens (28)...")

            def make_pe(dob: datetime) -> str:
                return f"PE-{dob.strftime('%Y%m%d')}-{random.randint(100000, 999999)}"

            samples = [
                # (first, last, dob_str,      phone,         lang, special_needs)
                ("David",    "Johnson",   "1988-03-15", "22501020304", "en", None),
                ("Mariam",   "Ouattara",  "1992-07-22", "22505060708", "fr", None),
                ("Aya",      "Bamba",     "1999-11-05", "22509101112", "fr", None),
                ("Paul",     "Kone",      "1990-05-14", "22513141516", "en", None),
                ("Fatou",    "Diallo",    "1985-11-20", "22517181920", "fr", None),
                ("Marc",     "Aka",       "2000-02-10", "22521222324", "en", None),
                ("Awa",      "Toure",     "1995-08-30", "22525262728", "fr", None),
                ("Seun",     "Adeyemi",   "1983-04-18", "22529303132", "en", None),
                ("Aisha",    "Coulibaly", "1997-12-03", "22533343536", "fr", "Mobilité réduite"),
                ("Kwame",    "Mensah",    "1975-06-25", "22537383940", "en", None),
                ("Nadia",    "Camara",    "2001-09-14", "22541424344", "fr", None),
                ("Ibrahima", "Sow",       "1968-01-08", "22545464748", "fr", "Déficience visuelle"),
                ("Grace",    "Asante",    "1994-03-27", "22549505152", "en", None),
                ("Yusuf",    "Traore",    "1989-10-11", "22553545556", "fr", None),
                ("Amina",    "Keita",     "2003-05-02", "22557585960", "fr", None),
                ("Kofi",     "Boateng",   "1978-08-19", "22561626364", "en", None),
                ("Chantal",  "N'Guessan", "1991-02-14", "22565666768", "fr", None),
                ("Moussa",   "Doumbia",   "1986-07-07", "22569707172", "fr", None),
                ("Esther",   "Koffi",     "1998-04-23", "22573747576", "en", None),
                ("Lamine",   "Barry",     "1972-09-01", "22577787980", "fr", "Déficience auditive"),
                ("Ramatou",  "Cisse",     "2002-11-16", "22581828384", "fr", None),
                ("Emmanuel", "Ofori",     "1980-06-12", "22585868788", "en", None),
                ("Mariame",  "Sylla",     "1993-01-29", "22589909192", "fr", None),
                ("Didier",   "Yao",       "1987-08-04", "22593949596", "fr", None),
                ("Fanta",    "Konate",    "2005-03-21", "22597989900", "fr", None),
                ("Serge",    "Gnagne",    "1976-12-09", "22501122334", "fr", None),
                ("Bintou",   "Diabate",   "1996-05-17", "22502233445", "fr", None),
                ("Alexis",   "Kouame",    "1984-10-30", "22503344556", "fr", None),
            ]

            for fname, lname, dob_str, phone, lang, special_needs in samples:
                dob = datetime.strptime(dob_str, "%Y-%m-%d")
                cit = Citizen(
                    first_name=fname,
                    last_name=lname,
                    date_of_birth=dob.date(),
                    pre_enrollment_code=make_pe(dob),
                    preferred_language=lang,
                    special_needs=special_needs,
                )
                cit.phone_number = phone
                db.session.add(cit)
                citizens_list.append(cit)

            db.session.commit()
        else:
            citizens_list = Citizen.query.limit(28).all()

        # ── Sample Queue Traffic ───────────────────────────────────────────────
        if Queue.query.count() == 0 and len(citizens_list) >= 8:
            print("Generating Sample Queue Traffic...")
            service_codes = list(db_services.keys())
            ticket_prefixes = {'NEW_APP': 'N', 'RENEWAL': 'R', 'COLLECTION': 'C', 'CORRECTION': 'L'}
            counters = {'NEW_APP': 1, 'RENEWAL': 1, 'COLLECTION': 1, 'CORRECTION': 1}

            queue_specs = [
                # (citizen_idx, svc_code,    status,       agent_idx, station_idx, mins_ago_created, mins_ago_called, mins_ago_done, wait, svc)
                (0,  'COLLECTION', 'assigned',    0, None, 15,  None, None, None, None),
                (1,  'RENEWAL',    'assigned',    1, None, 17,  None, None, None, None),
                (2,  'CORRECTION', 'assigned',    2, None, 17,  None, None, None, None),
                (3,  'NEW_APP',    'waiting',  None, None, 10,  None, None, None, None),
                (4,  'RENEWAL',    'waiting',  None, None,  8,  None, None, None, None),
                (5,  'COLLECTION', 'in_progress', 3, 3,    25,  10,   None, None, None),
                (6,  'NEW_APP',    'in_progress', 0, 0,    30,  12,   None, None, None),
                (7,  'CORRECTION', 'completed',   1, 1,    90,  75,   60,   15,   15),
            ]

            queues = []
            for (ci, svc, status, ai, si, mc, mcalled, mdone, wt, svct) in queue_specs:
                svc_obj = db_services[svc]
                prefix = ticket_prefixes[svc]
                num = counters[svc]
                counters[svc] += 1
                ticket_num = f"{prefix}-{num:03d}"

                q = Queue(
                    citizen_id=citizens_list[ci].id,
                    service_type_id=svc_obj.id,
                    ticket_number=ticket_num,
                    status=status,
                    priority_score=svc_obj.priority_level,
                    created_at=datetime.utcnow() - timedelta(minutes=mc),
                )
                if ai is not None:
                    q.agent_id = agents[ai].id
                if si is not None:
                    q.station_id = stations[si].id
                if mcalled is not None:
                    q.called_at = datetime.utcnow() - timedelta(minutes=mcalled)
                if mdone is not None:
                    q.completed_at = datetime.utcnow() - timedelta(minutes=mdone)
                    q.wait_time = wt
                    q.service_time = svct
                queues.append(q)

            db.session.add_all(queues)
            db.session.commit()

        print("\n========================================================")
        print("  Setup Complete! CNI Queue System seeded and ready.")
        print("========================================================\n")
        print("  Admin Login : ADMIN001 / admin123")
        print("  Agent Login : AGT001   / agent123  (Marie Kouassi)")
        print("                AGT002   / agent123  (Kofi Asante)")
        print("                AGT003   / agent123  (Ibrahim Traore)")
        print("                AGT004   / agent123  (Aminata Diallo)")
        print(f"\n  Citizens registered : {Citizen.query.count()}")
        print("\n  Start Server: cd src && python run.py\n")


app = create_app()

if __name__ == '__main__':
    if '--setup' in sys.argv:
        setup_database(app)
        sys.exit(0)

    socketio.run(app, debug=True)
