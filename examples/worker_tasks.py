def add(request):
    data = request.data
    return data['x'] + data['y']
