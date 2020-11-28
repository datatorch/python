from datatorch.core import upload
from pathlib import Path

url = "https://datatorchartifactstest.blob.core.windows.net/test/fi1.avro?sv=2019-12-12&ss=bfqt&srt=o&sp=rwdlacupx&se=2020-12-01T02:00:28Z&st=2020-11-28T18:00:28Z&spr=https&sig=gYm1SCWo0dnMv3dtkaSYc4%2FhW%2F9wk7CWgJWYPIfRgdg%3D"
url2 = "https://datatorchartifactstest.blob.core.windows.net/test/fi2.avro?sv=2019-12-12&ss=bfqt&srt=o&sp=rwdlacupx&se=2020-12-01T02:00:28Z&st=2020-11-28T18:00:28Z&spr=https&sig=gYm1SCWo0dnMv3dtkaSYc4%2FhW%2F9wk7CWgJWYPIfRgdg%3D"
url3 = "https://datatorchartifactstest.blob.core.windows.net/test/fi3.avro?sv=2019-12-12&ss=bfqt&srt=o&sp=rwdlacupx&se=2020-12-01T02:00:28Z&st=2020-11-28T18:00:28Z&spr=https&sig=gYm1SCWo0dnMv3dtkaSYc4%2FhW%2F9wk7CWgJWYPIfRgdg%3D"


event = upload.PutUploadEvent(Path("../test.avro"), url)
event2 = upload.PutUploadEvent(Path("../test2.avro"), url)
upload.get_upload_pool().enqueue(event)
upload.get_upload_pool().enqueue(event2)