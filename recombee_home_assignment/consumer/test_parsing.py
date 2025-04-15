import pytest

from consumer.consumer import FeedParsingException, parse_and_save_xml
from models.FeedItem import FeedItem

def test_valid_xml_with_multiple_items():
    with open("feed_example.xml", "r", encoding="utf-8") as f:
        xml = f.read()

    result = parse_and_save_xml(xml)
    assert isinstance(result, list)
    assert len(result) == 3
    assert isinstance(result[0], FeedItem)
    assert result[0].title == "Bodylab Men''s T-shirt - Black"
    assert isinstance(result[0].additional_image_link, list)

def test_valid_xml_with_single_item():
    xml = '''<?xml version="1.0"?>
    <rss xmlns:g="http://base.google.com/ns/1.0" version="2.0">
        <channel>
            <title>Feed Example</title>
            <link>recombee.com</link>
            <description></description>
            <item>
                <g:id>M0296</g:id>
                <title>Bodylab Men'';s T-shirt - Black</title>
                <description>desc</description>
                <link>https://bodylab.no/shop/mens-t-shirt-black-4059p.html</link>
                <g:image_link>https://www.bodylab.no/images/products/mens-t-shirt-black-p.jpg</g:image_link>
                <g:additional_image_link>
                    https://www.bodylab.no/images/products/mens-t-shirt-micro-chip-p.jpg</g:additional_image_link>
                <g:additional_image_link>
                    https://www.bodylab.no/images/products/minimum-deluxe-protein-bar-chocolate-chip-cookie-dough-p.png</g:additional_image_link>
                <g:price>299.00 NOK</g:price>
                <g:condition>new</g:condition>
                <g:availability>in stock</g:availability>
                <g:brand>Bodylab</g:brand>
                <g:gtin>5711657018069</g:gtin>
                <g:item_group_id>M0296</g:item_group_id>
                <g:sale_price></g:sale_price>
            </item>
        </channel>
    </rss>
    '''
        
    result = parse_and_save_xml(xml)
    assert len(result) == 1
    assert result[0].title == "Bodylab Men'';s T-shirt - Black"
    assert isinstance(result[0].additional_image_link, list)

def test_additional_image_link_as_string():
    with open("feed_example.xml", "r", encoding="utf-8") as f:
        xml = f.read()
        
    result = parse_and_save_xml(xml)
    assert isinstance(result[0].additional_image_link, list)
    assert len(result[0].additional_image_link) == 2

def test_invalid_xml_structure_raises_expat_error():
    xml = '<rss><channel><item><title>Broken'
    with pytest.raises(FeedParsingException, match="Unable to parse XML structure"):
        parse_and_save_xml(xml)

def test_missing_rss_channel_item_raises_exception():
    xml = '<rss><channel></channel></rss>'
    with pytest.raises(FeedParsingException, match="Missing 'rss.channel.item' structure"):
        parse_and_save_xml(xml)

def test_validation_error_raises_feed_parsing_exception():
    xml = '''
    <rss>
        <channel>
            <item>
                <g:additional_image_link>http://image.jpg</g:additional_image_link>
                <!-- missing required fields -->
            </item>
        </channel>
    </rss>
    '''
    with pytest.raises(FeedParsingException):
        parse_and_save_xml(xml)
