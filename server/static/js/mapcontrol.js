function createMapControl(map, jsonLayers, showNodeLink) {

  function renderCandidates(data) {
    let div = document.getElementById('address');
    if (div && data.length > 0) {
      let nearest = data[0].candidate;
      div.innerHTML = '「<a href="' + showNodeLink.replace("0", nearest.id)
      + '">' + nearest.fullname.join(' ')
      + '</a>」付近';
    }

    if (jsonLayers.length > 0) {
      for (const layer of jsonLayers) {
        map.off('click', layer.id);
        map.removeLayer(layer.id);
      }
      map.removeSource('triangle');
      jsonLayers = [];
    }

    let points = [];
    for (const i in data) {
      const node = data[i]['candidate'];
      let merged = false;
      for (let j = 0; j < points.length; j++) {
        if (points[j].geometry.coordinates[0] == node.x
            && points[j].geometry.coordinates[1] == node.y) {
          points[j].properties.names += ', ' + node.fullname.join('');
          merged = true;
          break;
        }
      }
      if (!merged) {
        points.push({
          'type': 'Feature',
          'geometry': {
            'type': 'Point',
            'coordinates': [node.x, node.y]
          },
          'properties': {
            'id': node.id,
            'names': node.fullname.join('')
          }
        });
      }
    }
    map.addSource('triangle', {
      'type': 'geojson',
      'data': {
        'type': 'FeatureCollection',
        'features': points
      }
    });

    jsonLayers.push({
      'id': 'nodes',
      'source': 'triangle',
      'type': 'circle',
      'paint': {
        'circle-stroke-color': '#FFFFFF',
        'circle-stroke-width': 2,
        'circle-stroke-opacity': 1,
        'circle-radius': 8,
        'circle-color': '#1e50a2',
        'circle-opacity': 0.5
      },
      'filter': ['==', '$type', 'Point']
    });
    for (const layer of jsonLayers) {
      map.addLayer(layer);
      map.on('click', layer.id, function (e) {
        const coordinates = e.features[0].geometry.coordinates.slice();
        let names = e.features[0].properties.names.toString();
        new maplibregl.Popup()
        .setLngLat(coordinates)
        .setHTML(names)
        .addTo(map);
      });
      map.on('mouseenter', layer.id, function () {
        map.getCanvas().style.cursor = 'pointer';
      });
      map.on('mouseleave', layer.id, function () {
        map.getCanvas().style.cursor = '';
      });
    }
  }

  function reverseGeocoding(lat, lng, zoom) {
    let level = parseInt(zoom, 10) - 7;
    if (level < 1) {
      level = 1;
    }
    fetch('/jsonrpc', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: 'jageocoder.reverse',
        params: {x: lng, y: lat, level: level},
        id: 1
      })
    }).then(res => res.json()
    ).then(rpcResponse => {
      if (rpcResponse.error) {
        console.error('JSONRPC error:', rpcResponse.error);
        return;
      }
      let data = rpcResponse.result;
      renderCandidates(data);
    });
  }

  return { renderCandidates, reverseGeocoding };
}
