# Ranking diario de búsquedas

La esfera actualmente muestra seis juegos destacados del piloto. **No los presenta como más buscados del día** porque GitHub Pages no puede agregar búsquedas de visitantes.

Para activar el ranking real, una API separada recibirá un evento solo cuando una persona elija un juego desde la búsqueda. Guardará `game_id`, día en zona `America/Costa_Rica` y un contador. No guardará el texto libre, IP ni identidad del visitante. El servidor validará que el `game_id` exista y limitará peticiones repetidas. Una tarea publicará cada día los seis IDs más buscados en un JSON pequeño que leerá la web; los juegos sin precio reciente se excluirán del panel de mejores precios.

El ranking es agregado por día y no equivale a popularidad global del juego. Hasta que exista ese servicio, la esfera muestra una selección del piloto sin llamarla «más buscados del día».
