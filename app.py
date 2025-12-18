from flask import Flask, render_template, jsonify, request
from database import init_db, get_all_servers, get_server_by_id, upsert_server
from api_client import fetch_servers

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


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


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
