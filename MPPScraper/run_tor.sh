#!/bin/bash

## Use proxy session: curl http://ifconfig.me --proxy socks5h://127.0.0.1:9050 : 109.70.100.23 |||  curl https://ifconfig.me : 103.93.222.234 ##
## Get new session: echo -e 'AUTHENTICATE ""\r\nsignal NEWNYM\r\nQUIT' | nc 127.0.0.1 9051 ##

port=${1:-9050}
data_dir="${2:-tmp}_${port}"
additional_options_file="${3:-torrc_additional}"

control_port=$(( ${port} + 1 ))
rm -rf "${data_dir}" && mkdir "${data_dir}"

tor \
  -f "${additional_options_file}" \
  --SOCKSPort ${port} \
  --ControlPort ${control_port} \
  --CookieAuthentication 0 \
  --DataDirectory "${data_dir}" \
  --GeoIPFile "${data_dir}/geoip" \
  --GeoIPv6File "${data_dir}/geoip6" 
