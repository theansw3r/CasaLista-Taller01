"""Consulta AWS CLI sin cambiar recursos ni imprimir credenciales."""
import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--region',required=True)
parser.add_argument('--instancia',required=True)
parser.add_argument('--salida',required=True)
args=parser.parse_args()

def aws(*comando):
    respuesta=subprocess.run(['aws','--region',args.region,*comando,'--output','json'],capture_output=True,text=True,check=True)
    return json.loads(respuesta.stdout)

instancias=aws('ec2','describe-instances','--instance-ids',args.instancia)
instancia=instancias['Reservations'][0]['Instances'][0]
assert instancia['State']['Name']=='running','La instancia no está encendida'
direcciones=aws('ec2','describe-addresses','--filters',f'Name=instance-id,Values={args.instancia}')['Addresses']
assert len(direcciones)==1,'No existe una única IP elástica asociada a esta instancia'
eip=direcciones[0]
assert eip.get('AssociationId') and eip.get('AllocationId'),'La IP no tiene asociación elástica verificable'
assert instancia.get('PublicIpAddress')==eip['PublicIp'],'La IP de la instancia no coincide con la EIP'
reporte={'fecha_utc':datetime.now(timezone.utc).isoformat(),'region':args.region,
         'instancia':args.instancia,'estado':'running','ip_elastica':eip['PublicIp'],
         'asociacion':eip['AssociationId'],'asignacion':eip['AllocationId']}
p=Path(args.salida);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(reporte,indent=2)+'\n')
print('Estado Running y asociación de IP elástica comprobados; evidencia guardada.')
