"""
RSS Feed 生成模块
生成播客的 RSS XML 文件
"""

import os
from datetime import datetime
from typing import Dict, Any, List
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom


class RSSGenerator:
    """RSS 生成器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.podcast = config.get('podcast', {})
        self.paths = config.get('paths', {})
        self.resources = config.get('resources', {})
    
    def generate(self, episodes: List[Dict[str, Any]]) -> str:
        """
        生成 RSS XML 字符串
        
        Args:
            episodes: 节目列表
            
        Returns:
            str: RSS XML 字符串
        """
        # 创建根元素
        rss = Element('rss')
        rss.set('version', '2.0')
        rss.set('xmlns:itunes', 'http://www.itunes.com/dtds/podcast-1.0.dtd')
        rss.set('xmlns:content', 'http://purl.org/rss/1.0/modules/content/')
        
        # 创建 channel
        channel = SubElement(rss, 'channel')
        
        # 添加播客基本信息
        self._add_podcast_info(channel)
        
        # 添加节目条目
        for episode in episodes:
            self._add_episode(channel, episode)
        
        # 格式化 XML
        xml_string = tostring(rss, encoding='unicode')
        dom = minidom.parseString(xml_string)
        pretty_xml = dom.toprettyxml(indent='  ')
        
        # 移除空行
        lines = [line for line in pretty_xml.split('\n') if line.strip()]
        return '\n'.join(lines)
    
    def _add_podcast_info(self, channel: Element):
        """添加播客基本信息"""
        # 必填字段
        title = SubElement(channel, 'title')
        title.text = self.podcast.get('title', 'GhostRadio')
        
        link = SubElement(channel, 'link')
        link.text = self.podcast.get('base_url', '')
        
        description = SubElement(channel, 'description')
        description.text = self.podcast.get('description', 'AI Generated Podcast')
        
        language = SubElement(channel, 'language')
        language.text = self.podcast.get('language', 'zh-CN')
        
        # iTunes 特有字段
        itunes_author = SubElement(channel, 'itunes:author')
        itunes_author.text = self.podcast.get('author', 'GhostRadio')
        
        itunes_category = SubElement(channel, 'itunes:category')
        itunes_category.set('text', self.podcast.get('category', 'Technology'))
        
        itunes_explicit = SubElement(channel, 'itunes:explicit')
        itunes_explicit.text = 'false'
        
        # 封面图片
        cover_image = self.podcast.get('cover_image', 'cover.jpg')
        if cover_image:
            itunes_image = SubElement(channel, 'itunes:image')
            itunes_image.set('href', f"{self.podcast.get('base_url', '')}/{cover_image}")
            
            image = SubElement(channel, 'image')
            image_url = SubElement(image, 'url')
            image_url.text = f"{self.podcast.get('base_url', '')}/{cover_image}"
            image_title = SubElement(image, 'title')
            image_title.text = self.podcast.get('title', 'GhostRadio')
            image_link = SubElement(image, 'link')
            image_link.text = self.podcast.get('base_url', '')
        
        # 最后生成时间
        last_build = SubElement(channel, 'lastBuildDate')
        last_build.text = self._format_rfc822_date(datetime.now())
        
        # 生成器
        generator = SubElement(channel, 'generator')
        generator.text = 'GhostRadio'
    
    def _add_episode(self, channel: Element, episode: Dict[str, Any]):
        """添加单个节目条目"""
        item = SubElement(channel, 'item')
        
        # 标题
        title = SubElement(item, 'title')
        title.text = episode.get('title', 'Untitled')
        
        # 描述
        description = SubElement(item, 'description')
        description.text = episode.get('description', f"Episode {episode.get('id', '')}")
        
        # 链接
        link = SubElement(item, 'link')
        link.text = episode.get('url', '')
        
        # 发布日期
        pub_date = SubElement(item, 'pubDate')
        created = episode.get('created')
        if isinstance(created, datetime):
            pub_date.text = self._format_rfc822_date(created)
        else:
            pub_date.text = self._format_rfc822_date(datetime.now())
        
        # GUID (全局唯一标识符)
        guid = SubElement(item, 'guid')
        guid.set('isPermaLink', 'false')
        guid.text = episode.get('id', '')
        
        # 音频文件附件
        audio_file = episode.get('audio_file', '')
        if audio_file:
            enclosure = SubElement(item, 'enclosure')
            
            # 构建完整 URL
            base_url = self.podcast.get('base_url', '')
            audio_filename = os.path.basename(audio_file)
            audio_url = f"{base_url}/episodes/{audio_filename}"
            enclosure.set('url', audio_url)
            
            # 文件大小
            size_bytes = episode.get('size_mb', 0) * 1024 * 1024
            enclosure.set('length', str(int(size_bytes)))
            
            # MIME 类型
            audio_format = self.resources.get('audio_format', 'm4a')
            mime_type = self._get_mime_type(audio_format)
            enclosure.set('type', mime_type)
            
            # 时长 (iTunes)
            duration = episode.get('duration', 0)
            if duration > 0:
                itunes_duration = SubElement(item, 'itunes:duration')
                itunes_duration.text = self._format_duration(duration)
        
        # iTunes 特有字段
        itunes_author = SubElement(item, 'itunes:author')
        itunes_author.text = self.podcast.get('author', 'GhostRadio')
        
        itunes_explicit = SubElement(item, 'itunes:explicit')
        itunes_explicit.text = 'false'
    
    def _format_rfc822_date(self, dt: datetime) -> str:
        """格式化日期为 RFC 822 格式"""
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        day_name = days[dt.weekday()]
        month_name = months[dt.month - 1]
        
        return f"{day_name}, {dt.day:02d} {month_name} {dt.year} {dt.hour:02d}:{dt.minute:02d}:{dt.second:02d} +0000"
    
    def _format_duration(self, seconds: float) -> str:
        """格式化时长为 HH:MM:SS 格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
    
    def _get_mime_type(self, audio_format: str) -> str:
        """获取音频格式的 MIME 类型"""
        mime_types = {
            'mp3': 'audio/mpeg',
            'm4a': 'audio/mp4',
            'mp4': 'audio/mp4',
            'aac': 'audio/aac',
            'ogg': 'audio/ogg',
            'opus': 'audio/ogg'
        }
        return mime_types.get(audio_format.lower(), 'audio/mpeg')
    
    def save_rss(self, episodes: List[Dict[str, Any]], output_path: str = None):
        """
        生成并保存 RSS 文件
        
        Args:
            episodes: 节目列表
            output_path: 输出文件路径（默认为配置中的路径）
        """
        if output_path is None:
            output_path = self.paths.get('rss_file', 'episodes/feed.xml')
        
        # 确保目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 生成 RSS
        rss_content = self.generate(episodes)
        
        # 保存文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rss_content)
        
        return output_path
