# Laboratorio virtual CSR1000v del Grupo 1

[Editable Draw.io](Topologia_Laboratorio_CSR1000v_Grupo1.drawio) · [Imagen PNG](Topologia_Laboratorio_CSR1000v_Grupo1.png) · [PDF vectorial](Topologia_Laboratorio_CSR1000v_Grupo1.pdf).

Fuente: dieciséis imágenes de Capturas.docx aportadas en el RAR. Se revisaron las imágenes originales. El archivo íntegro permanece privado porque incluye datos domésticos/VPN, identificadores del dispositivo y material de claves que no son necesarios para la entrega.

| Dato | Evidencia aportada |
|---|---|
| Un anfitrión Windows con VirtualBox | Imágenes 1 y 2; la VM y la aplicación coexisten en el mismo computador |
| VM ETW-CSR1000v y adaptador solo-anfitrión | Imágenes 1, 2 y 15 |
| Host 192.168.56.1/24 y subred 192.168.56.0/24 | Imágenes 11, 15 y 16 |
| CSR1000v, GigabitEthernet1, 192.168.56.105, up/up | [Captura original seleccionada](Capturas/Interfaz_CSR1000v.png), imagen 5; imagen 16 confirma /24 |
| IOS XE 16.09.05 | Imagen 6, salida show version |
| Ping exitoso, cuatro respuestas sin pérdida | Imagen 10 |
| TCP/22 accesible desde el adaptador Host-Only | [Captura original seleccionada](Capturas/Prueba_TCP22_CSR1000v.png), imagen 11, TcpTestSucceeded=True |
| NetAudit y resultados posteriores | Imágenes 12–14: 24 evaluaciones; corresponden al estado de Fase 3 y no se atribuyen al cierre de Fase 2 |

El gráfico separa vista física y lógica, ancla solicitud y retorno a los componentes y no añade switches, VLAN, OSPF, servidores ni GNS3. Las direcciones publicadas pertenecen exclusivamente al laboratorio autorizado para este diagrama. No se publican credenciales, números de serie o direcciones domésticas/VPN.

Se comprobó el XML en el editor real de Draw.io: diez formas y cuatro conectores, con etiquetas y conexiones visibles. PNG y PDF fueron generados desde la misma geometría y revisados. No se realizó una nueva conexión SSH ni se presenta la topología como validación de producción.
