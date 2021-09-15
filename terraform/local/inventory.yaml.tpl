data_path: ${abspath("../../mitogen/local")}
servers:
%{ for server in servers ~}
    - name: ${server.machine_names[0]}
      count: ${server.env["SERVER_INDEX"]}
      ssh_hostname: '${server.ssh_config[0].host}'
      ssh_port: ${server.ssh_config[0].port}
      ssh_key: '${abspath("../../mitogen/local/configs/ssh-private-${server.machine_names[0]}.key")}'
      ssh_user: '${server.ssh_config[0].user}'
%{ endfor ~}
