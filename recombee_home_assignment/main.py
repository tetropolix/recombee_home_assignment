from fastapi import FastAPI, HTTPException, Request
from xml.parsers.expat import ExpatError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
import xmltodict

from models.Feed import Feed

app = FastAPI()

@app.post("/feeds")
async def upload_feed(request: Request):
    # we may also check for the Content-type header

    try:
        request_xml = await request.body()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading request body: {str(e)}")

    try:
        xml_as_dict = xmltodict.parse(request_xml)
    except ExpatError:
        raise HTTPException(status_code=400, detail="Unable to parse XML structure")

    try:
        items = xml_as_dict['rss']['channel']['item']
    except (KeyError, TypeError):
        raise HTTPException(status_code=422, detail="Missing 'rss.channel.item' structure in XML")

    
    if isinstance(items, dict):
        items = [items]

    try:
        feed_items = [Feed(**item) for item in items]
    except ValidationError as ve:
        return JSONResponse(
            status_code=422,
            content={"detail": ve.errors()}
        )

    return JSONResponse(
        status_code=200,
        content={"message": "Feed uploaded successfully", "items_count": len(feed_items)}
    )