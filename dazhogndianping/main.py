import math
import re
import requests as rq
from lxml import etree
import copyheaders

headers=b"""
Accept: application/json, text/javascript, */*; q=0.01
Origin: http://www.dianping.com
Referer: http://www.dianping.com/
User-Agent: Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36
Cookie: cy=3; cye=hangzhou; _lx_utm=utm_source%3DBaidu%26utm_medium%3Dorganic; _lxsdk_cuid=169fb69c97dc8-0963f328c3b73d-58422116-144000-169fb69c97ec8; _lxsdk=169fb69c97dc8-0963f328c3b73d-58422116-144000-169fb69c97ec8; _hc.v=3536e3e1-374f-a698-f601-d9f4d1987a9d.1554701209; s_ViewType=10; _lxsdk_s=169fb869355-209-4d9-a92%7C%7C41
"""

headers=copyheaders.headers_raw_to_dict(headers)


def get_css(conn_text):
    """
    获取css_url 和 对应css.class的tag
    :param conn_text:
    :return:  css_url,tag
    """
    match=re.search(r'href="(.*?svgtextcss.*?css)"',conn_text,re.M)
    if not match:
        raise Exception("cannot find svg url")
    css_url=match.group(1)

    css_url="https:"+css_url

    html=etree.HTML(conn_text)
    tag=html.xpath("(//b/span[@class])[1]/@class")[0][0:3]

    return css_url,tag


def get_css_to_px_dict(css_url):
    """
    根据css_url 来获取 不同class 对应的 offset和position
    :param css_url:
    :return: offset,position
    """
    conn_text=rq.get(css_url,headers=headers).text
    css_datas=re.findall(r"(.\w+){background:(-\d+.\d+)px (-\d+.\d+)px",conn_text)
    css_to_px_dict={}
    for data in css_datas:
        css_name=data[0][1:]
        offset=abs(float(data[1]))
        position=abs(float(data[2]))
        css_to_px_dict[css_name]=[offset,position]
    return  css_to_px_dict


def get_svg_value_to_threshold_dict(tag,css_url):
    """
    根据tag和css_url 得到 不同像素对应的value位置dict
    :param tag:
    :param css_url:
    :return: dict {'value_str':'range'}
    """
    conn_text=rq.get(css_url,headers=headers).text
    svg_url_match=re.search(r'span\[class\^="%s"\].*?background-image: url\((.*?)\)' % tag,conn_text)
    if not svg_url_match:
        raise Exception("not find svg url")

    svg_url="https:"+svg_url_match.group(1)

    svg_conn_text=rq.get(svg_url,headers=headers).content
    selector=etree.HTML(svg_conn_text)

    texts=selector.xpath("//text")

    svg_value_to_threshold_dicts={}

    last=1
    for text in texts:
        y=int(text.xpath("./@y")[0])
        values=text.xpath("./text()")[0]
        svg_value_to_threshold_dicts[values]=range(last,y+1)
        last=y+1

    return svg_value_to_threshold_dicts


def run(url):
    conn_text=rq.get(url,headers=headers).text
    css_url,tag=get_css(conn_text)
    css_to_px_dict=get_css_to_px_dict(css_url)
    svg_value_to_threshold_dict=get_svg_value_to_threshold_dict(tag,css_url)

    selector=etree.HTML(conn_text)

    shops=selector.xpath('//div[contains(@class,"shop-list")]//li')

    for shop in shops:
        name=shop.xpath(".//div[@class='tit']/a[1]/h4/text()")[0]

        review_num=0
        price=0

        comments=shop.xpath('.//div[@class="comment"]')
        for comment in comments:

            review_num_datas=comment.xpath("./a[@class='review-num']/b/node()")
            for review_num_node in review_num_datas:
                if isinstance(review_num_node,etree._ElementStringResult) or isinstance(review_num_node,etree._ElementUnicodeResult):
                    review_num=review_num*10+int(review_num_node)
                else:
                    css_name=review_num_node.attrib['class']
                    offset,position=css_to_px_dict[css_name]

                    for k,v in svg_value_to_threshold_dict.items():
                        if position in v:
                            index=int(math.ceil(offset/12))
                            value=int(k[index-1])
                            review_num=review_num*10+value

            price_datas=comment.xpath("./a[@class='mean-price']/b/node()")
            for price_node in price_datas:

                if isinstance(price_node,etree._ElementUnicodeResult):
                    if len(price_node)>1:
                        price=price*10+int(price_node[1:])
                elif isinstance(price_node,etree._ElementStringResult):
                    price=price*10+int(price_node)
                else:
                    css_name=price_node.attrib['class']
                    offset,position=css_to_px_dict[css_name]

                    for k,v in svg_value_to_threshold_dict.items():
                        if position in v:
                            index=int(math.ceil(offset/12))
                            value=int(k[index-1])
                            price=price*10+value


        taste=service=env=''

        comment_lists=shop.xpath(".//span[@class='comment-list']/span")
        for item_datas in comment_lists:
            if item_datas.xpath("./text()") and item_datas.xpath("./text()")[0]==u"口味":
                item_data=item_datas.xpath("./b/node()")
                for item_node in item_data:
                    if isinstance(item_node,etree._Element):
                        css_name=item_node.attrib['class']
                        offset,position=css_to_px_dict[css_name]

                        for k,v in svg_value_to_threshold_dict.items():
                            if position in v:
                                index = int(math.ceil(offset / 12))
                                value = (k[index - 1])
                                taste+=value

                    else:
                        taste+=item_node

            if item_datas.xpath("./text()") and item_datas.xpath("./text()")[0]==u"服务":
                item_data=item_datas.xpath("./b/node()")
                for item_node in item_data:
                    if isinstance(item_node,etree._Element):
                        css_name=item_node.attrib['class']
                        offset,position=css_to_px_dict[css_name]

                        for k,v in svg_value_to_threshold_dict.items():
                            if position in v:
                                index = int(math.ceil(offset / 12))
                                value = (k[index - 1])
                                service+=value

                    else:
                        service+=item_node

            if item_datas.xpath("./text()") and item_datas.xpath("./text()")[0]==u"环境":
                item_data=item_datas.xpath("./b/node()")
                for item_node in item_data:
                    if isinstance(item_node,etree._Element):
                        css_name=item_node.attrib['class']
                        offset,position=css_to_px_dict[css_name]

                        for k,v in svg_value_to_threshold_dict.items():
                            if position in v:
                                index = int(math.ceil(offset / 12))
                                value = (k[index - 1])
                                env+=value

                    else:
                        env+=item_node

        item={
            'name':name,
            'review_num':review_num,
            'price':price,
            'taste':float(taste),
            'service':float(service),
            'environment':float(env),
        }
        print(item)


if __name__ == '__main__':
    url="https://www.dianping.com/hangzhou/ch10/g110"
    run(url)