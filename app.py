from flask import Flask, render_template, jsonify, request
from database import (init_db, get_all_servers, get_server_by_id, upsert_server,
                      upsert_server_inventory, get_all_bios, get_all_bmc)
from api_client import fetch_servers, fetch_server_inventory

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/bios')
def bios_page():
    return render_template('bios.html')


@app.route('/bmc')
def bmc_page():
    return render_template('bmc.html')


@app.route('/api/servers', methods=['GET'])
def api_get_servers():
    servers = get_all_servers()
    return jsonify(servers)


@app.route('/api/servers/<int:server_id>', methods=['GET'])
def api_get_server(server_id):
    server = get_server_by_id(server_id)
    if server:
        return jsonify(server)
    return jsonify({'error': 'Server not found'}), 404


@app.route('/api/sync', methods=['POST'])
def sync_servers():
    try:
        servers = fetch_servers()
        synced_count = 0

        for server in servers:
            upsert_server(server)
            synced_count += 1

        return jsonify({
            'success': True,
            'message': f'Successfully synced {synced_count} servers',
            'count': synced_count
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/sync-inventory', methods=['POST'])
def sync_inventory():
    try:
        servers = get_all_servers()
        synced_count = 0
        errors = []

        for server in servers:
            try:
                inventory = fetch_server_inventory(server['id'])
                upsert_server_inventory(server['id'], inventory)
                synced_count += 1
            except Exception as e:
                errors.append(f"{server['hostname']}: {str(e)}")

        return jsonify({
            'success': True,
            'message': f'Successfully synced inventory for {synced_count} servers',
            'count': synced_count,
            'errors': errors
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/bios', methods=['GET'])
def api_get_bios():
    bios_data = get_all_bios()
    return jsonify(bios_data)


@app.route('/api/bmc', methods=['GET'])
def api_get_bmc():
    bmc_data = get_all_bmc()
    return jsonify(bmc_data)


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)
