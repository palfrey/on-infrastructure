data_path: ${abspath("../../mitogen/prod")}
servers:
%{ for server in servers ~}
    - name: ${server.name}
      count: ${index(servers, server)}
      ssh_hostname: '${server.public_ipv4address}'
      ssh_port: 22
      ssh_key: '${abspath("../../mitogen/prod/configs/ssh-private-${server.name}.key")}'
      ssh_user: 'root'
%{ endfor ~}
