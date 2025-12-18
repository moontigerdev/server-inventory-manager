import sqlite3
import json
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / "servers.db"


def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS servers (
            id INTEGER PRIMARY KEY,
            hostname TEXT,
            servername TEXT,
            os TEXT,
            primary_ip TEXT,
            power_status TEXT,
            server_type TEXT,
            tags TEXT,
            description TEXT,
            assignment_date TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS server_hardware (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER NOT NULL,
            cpu_model TEXT,
            cpu_count INTEGER,
            cpu_cores INTEGER,
            cpu_threads INTEGER,
            cpu_mhz TEXT,
            cpu_mhz_turbo TEXT,
            memory_total_mb INTEGER,
            memory_count INTEGER,
            memory_details TEXT,
            disk_total_mib REAL,
            disk_count INTEGER,
            disk_details TEXT,
            mainboard_model TEXT,
            mainboard_version TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (server_id) REFERENCES servers (id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS server_ips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER NOT NULL,
            ip_address TEXT NOT NULL,
            is_primary INTEGER DEFAULT 0,
            is_ipv4 INTEGER DEFAULT 1,
            is_ipv6 INTEGER DEFAULT 0,
            subnet TEXT,
            netmask TEXT,
            gateway TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (server_id) REFERENCES servers (id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS server_bios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER NOT NULL,
            model TEXT,
            value TEXT,
            serial TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (server_id) REFERENCES servers (id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS server_bmc (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER NOT NULL,
            model TEXT,
            value TEXT,
            serial TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (server_id) REFERENCES servers (id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()


def upsert_server(server_data):
    conn = get_db_connection()
    cursor = conn.cursor()

    tags = json.dumps(server_data.get('tags', []))

    cursor.execute('''
        INSERT OR REPLACE INTO servers
        (id, hostname, servername, os, primary_ip, power_status, server_type, tags, description, assignment_date, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (
        server_data.get('id'),
        server_data.get('hostname'),
        server_data.get('servername'),
        server_data.get('os'),
        server_data.get('primaryip'),
        server_data.get('cachedPowerstatus'),
        server_data.get('typeOfServer'),
        tags,
        server_data.get('description'),
        server_data.get('assignmentDate')
    ))

    server_id = server_data.get('id')

    # Handle hardware information
    hardware = server_data.get('detailedHardwareInformation', {})
    if hardware:
        cursor.execute('DELETE FROM server_hardware WHERE server_id = ?', (server_id,))

        cpu = hardware.get('cpu', {})
        memory = hardware.get('memory', {})
        disk = hardware.get('disk', {})
        mainboard = hardware.get('mainboard', {})

        cursor.execute('''
            INSERT INTO server_hardware
            (server_id, cpu_model, cpu_count, cpu_cores, cpu_threads, cpu_mhz, cpu_mhz_turbo,
             memory_total_mb, memory_count, memory_details, disk_total_mib, disk_count, disk_details,
             mainboard_model, mainboard_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            server_id,
            cpu.get('model'),
            cpu.get('count'),
            cpu.get('cores'),
            cpu.get('threads'),
            cpu.get('value'),
            str(cpu.get('mhzTurbo', '')),
            memory.get('value'),
            memory.get('count'),
            json.dumps(memory.get('details', [])),
            disk.get('value'),
            disk.get('count'),
            json.dumps(disk.get('details', [])),
            mainboard.get('model'),
            mainboard.get('value')
        ))

    # Handle IP assignments
    ip_assignments = server_data.get('ipassignments', [])
    cursor.execute('DELETE FROM server_ips WHERE server_id = ?', (server_id,))

    for ip_info in ip_assignments:
        ip_attrs = ip_info.get('ipAttributes', {})
        subnet_info = ip_info.get('subnetinformation', {})

        cursor.execute('''
            INSERT INTO server_ips
            (server_id, ip_address, is_primary, is_ipv4, is_ipv6, subnet, netmask, gateway)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            server_id,
            ip_info.get('ip'),
            ip_info.get('primary_ip', 0),
            ip_attrs.get('isIpv4', 0),
            ip_attrs.get('isIpv6', 0),
            subnet_info.get('subnet'),
            subnet_info.get('netmask'),
            subnet_info.get('gw')
        ))

    conn.commit()
    conn.close()


def get_all_servers():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT s.*, sh.cpu_model, sh.cpu_count, sh.cpu_cores, sh.cpu_threads, sh.cpu_mhz, sh.cpu_mhz_turbo,
               sh.memory_total_mb, sh.memory_count, sh.disk_total_mib, sh.disk_count,
               sh.mainboard_model, sh.mainboard_version
        FROM servers s
        LEFT JOIN server_hardware sh ON s.id = sh.server_id
        ORDER BY s.hostname
    ''')

    servers = []
    for row in cursor.fetchall():
        server = dict(row)
        server['tags'] = json.loads(server.get('tags', '[]'))

        # Get IP addresses for this server
        cursor.execute('SELECT * FROM server_ips WHERE server_id = ?', (server['id'],))
        server['ip_addresses'] = [dict(ip) for ip in cursor.fetchall()]

        servers.append(server)

    conn.close()
    return servers


def get_server_by_id(server_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT s.*, sh.cpu_model, sh.cpu_count, sh.cpu_cores, sh.cpu_threads, sh.cpu_mhz, sh.cpu_mhz_turbo,
               sh.memory_total_mb, sh.memory_count, sh.memory_details, sh.disk_total_mib, sh.disk_count,
               sh.disk_details, sh.mainboard_model, sh.mainboard_version
        FROM servers s
        LEFT JOIN server_hardware sh ON s.id = sh.server_id
        WHERE s.id = ?
    ''', (server_id,))

    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    server = dict(row)
    server['tags'] = json.loads(server.get('tags', '[]'))
    server['memory_details'] = json.loads(server.get('memory_details', '[]') or '[]')
    server['disk_details'] = json.loads(server.get('disk_details', '[]') or '[]')

    cursor.execute('SELECT * FROM server_ips WHERE server_id = ?', (server_id,))
    server['ip_addresses'] = [dict(ip) for ip in cursor.fetchall()]

    conn.close()
    return server


def upsert_server_inventory(server_id, inventory_data):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Clear existing BIOS and BMC data for this server
    cursor.execute('DELETE FROM server_bios WHERE server_id = ?', (server_id,))
    cursor.execute('DELETE FROM server_bmc WHERE server_id = ?', (server_id,))

    for item in inventory_data:
        root_component = item.get('root_component', {})
        component_desc = root_component.get('description', '')

        if component_desc == 'BIOS':
            cursor.execute('''
                INSERT INTO server_bios (server_id, model, value, serial)
                VALUES (?, ?, ?, ?)
            ''', (
                server_id,
                item.get('model'),
                item.get('value'),
                item.get('serial')
            ))
        elif component_desc == 'BMC Version':
            cursor.execute('''
                INSERT INTO server_bmc (server_id, model, value, serial)
                VALUES (?, ?, ?, ?)
            ''', (
                server_id,
                item.get('model'),
                item.get('value'),
                item.get('serial')
            ))

    conn.commit()
    conn.close()


def get_all_bios():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT s.id, s.hostname, s.servername, s.primary_ip,
               b.model, b.value, b.serial, b.last_updated
        FROM servers s
        LEFT JOIN server_bios b ON s.id = b.server_id
        ORDER BY s.hostname
    ''')

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_all_bmc():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT s.id, s.hostname, s.servername, s.primary_ip,
               b.model, b.value, b.serial, b.last_updated
        FROM servers s
        LEFT JOIN server_bmc b ON s.id = b.server_id
        ORDER BY s.hostname
    ''')

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results
