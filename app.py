import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import xml.etree.ElementTree as ET

# ================= 配置区 =================
# 你刚刚提供的真实 DeepSeek API Key
API_KEY = "sk-547ca0352aab49b6a75fd75a6f3e43a5"

# DeepSeek 的专属配置
API_URL = "https://api.deepseek.com/chat/completions"
MODEL_NAME = "deepseek-chat"
# ==========================================

st.set_page_config(page_title="科技前沿 AI 监控", page_icon="🤖", layout="centered")

class WebMonitor:
    def __init__(self):
        self.sources = {
            "机器之心": "https://www.jiqizhixin.com/rss",
            "量子位": "https://www.qbitai.com/feed"
        }

    def get_article_content(self, url):
        """爬取文章全文，供 AI 阅读"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=10)
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 提取所有段落文本
            paragraphs = soup.find_all('p')
            content = " ".join([p.get_text() for p in paragraphs])
            
            # 截取前 2000 字给 AI (DeepSeek 足够聪明，前两千字足够提炼核心了)
            return content[:2000]
        except Exception as e:
            return ""

    def summarize_with_ai(self, content):
        """调用 DeepSeek 生成一句话摘要"""
        if not content.strip() or not API_KEY:
            return "⚠️ 没抓取到正文内容，AI 无法总结。"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }
        
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": "你是一个资深科技编辑。请用极其精炼的1-2句话，总结下面这篇文章的核心内容。直接输出结果，不要废话。"},
                {"role": "user", "content": f"文章内容：\n{content}"}
            ]
        }

        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            return f"🤖 DeepSeek 总结失败，可能是额度不足或网络波动: {str(e)}"

    def fetch_articles(self, site_name, days_limit):
        """获取并过滤文章"""
        url = self.sources.get(site_name)
        if not url: return []

        threshold_date = datetime.now() - timedelta(days=days_limit)
        articles = []

        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=10)
            resp.encoding = 'utf-8'
            
            xml_data = re.sub(r'\sxmlns="[^"]+"', '', resp.text, count=1)
            root = ET.fromstring(xml_data)

            for item in root.findall('.//item'):
                title = item.find('title')
                link = item.find('link')
                pub_date = item.find('pubDate')

                article_title = title.text if title is not None else "无标题"
                article_link = link.text.strip() if link is not None else ""
                article_time_str = pub_date.text if pub_date is not None else ""

                try:
                    if article_time_str:
                        clean_time = article_time_str.split('+')[0].strip()
                        dt = datetime.strptime(clean_time, '%a, %d %b %Y %H:%M:%S')
                        # 按你要求：过滤掉超过设定天数的文章
                        if dt < threshold_date:
                            continue
                        formatted_time = dt.strftime('%Y-%m-%d %H:%M')
                    else:
                        formatted_time = "未知时间"
                except:
                    continue

                articles.append({
                    "title": article_title,
                    "link": article_link,
                    "time": formatted_time,
                    "source": site_name
                })

            return articles
        except Exception as e:
            return []

# ================= 网页 UI 部分 =================
st.title("📱 科技资讯 AI 监控站")
st.markdown("从官网直连获取最新资讯，并由 **DeepSeek 大模型** 自动生成硬核摘要。")

with st.sidebar:
    st.header("⚙️ 监控设置")
    days_to_fetch = st.slider("获取多少天内的文章？", min_value=1, max_value=7, value=1)
    
    start_btn = st.button("🚀 立即获取并让 AI 总结", type="primary")
    
    st.markdown("---")
    st.caption("提示：用手机连接电脑同局域网的 WiFi，输入本网页的 Network URL 即可访问。")

monitor = WebMonitor()

if start_btn:
    with st.spinner(f'正在前往官网抓取 {days_to_fetch} 天内的新闻，并呼叫 DeepSeek...'):
        all_articles = []
        for name in monitor.sources.keys():
            all_articles.extend(monitor.fetch_articles(name, days_to_fetch))
        
        all_articles.sort(key=lambda x: x['time'], reverse=True)
        
        if not all_articles:
            st.warning("这段时间没有新文章，或者网络开小差了。")
        else:
            st.success(f"共发现 {len(all_articles)} 篇新鲜资讯！")
            
            for art in all_articles:
                with st.container():
                    st.subheader(f"【{art['source']}】{art['title']}")
                    st.caption(f"发布时间: {art['time']}")
                    
                    # 抓全文 -> 丢给 DeepSeek -> 拿回摘要
                    full_text = monitor.get_article_content(art['link'])
                    summary = monitor.summarize_with_ai(full_text)
                    
                    st.info(f"**🤖 DeepSeek 划重点：**\n\n{summary}")
                    st.markdown(f"[👉 点击这里阅读原文]({art['link']})")
                    st.divider()
