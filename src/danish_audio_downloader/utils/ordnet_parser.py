"""
Parser for extracting dictionary data from Ordnet.dk.
"""

import re
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup, Tag


class OrdnetParser:
    """Parser for extracting dictionary information from Ordnet.dk pages."""
    
    @staticmethod
    def parse_word_data(soup: BeautifulSoup, word: str) -> Dict:
        """
        Extract comprehensive word data from an Ordnet.dk page.
        
        Args:
            soup: BeautifulSoup object of the Ordnet.dk page
            word: The original word being searched for
            
        Returns:
            dict: Dictionary containing word information
        """
        word_data = {
            'word': word,
            'original_word': word,
            'pronunciation': '',
            'word_type': '',
            'gender': '',
            'plural': '',
            'inflections': '',
            'danish_definition': '',
            'english_translation': '',
            'audio_url': '',
            'ordnet_found': False,
            'error': ''
        }
        
        try:
            # Check if we found a valid word entry
            main_content = soup.find('div', class_='searchResultBox')
            if not main_content:
                word_data['error'] = 'No search results found'
                return word_data
            
            # Look for the word entry - it might not be directly inside searchResultBox
            word_entry = soup.find('div', class_='definitionBoxTop')
            if not word_entry:
                word_data['error'] = 'No word definition found'
                return word_data
            
            word_data['ordnet_found'] = True
            
            # Extract pronunciation
            word_data['pronunciation'] = OrdnetParser._extract_pronunciation(soup)
            
            # Extract word type and grammatical information
            word_data['word_type'] = OrdnetParser._extract_word_type(word_entry)
            word_data['gender'] = OrdnetParser._extract_gender(word_entry)
            word_data['plural'] = OrdnetParser._extract_plural(word_entry)
            word_data['inflections'] = OrdnetParser._extract_inflections(word_entry)
            
            # Extract Danish definition
            word_data['danish_definition'] = OrdnetParser._extract_definition(word_entry)
            
            # Extract English translation (if available)
            word_data['english_translation'] = OrdnetParser._extract_english_translation(word_entry)
            
            # Extract audio URL
            word_data['audio_url'] = OrdnetParser._extract_audio_url(soup)
            
        except Exception as e:
            word_data['error'] = f'Error parsing Ordnet data: {str(e)}'
        
        return word_data
    
    @staticmethod
    def _extract_pronunciation(soup: BeautifulSoup) -> str:
        """Extract pronunciation from the page."""
        try:
            # Look for pronunciation section
            udtale_div = soup.find('div', id='id-udt')
            if udtale_div:
                # Find pronunciation in lydskrift spans
                lydskrift_spans = udtale_div.find_all('span', class_='lydskrift')
                if lydskrift_spans:
                    # Get the first pronunciation (usually the main one)
                    pronunciation_text = lydskrift_spans[0].get_text(strip=True)
                    
                    # Clean up the pronunciation - it should already have brackets
                    pronunciation_text = pronunciation_text.strip()
                    
                    # Convert to standard IPA format if needed
                    if pronunciation_text.startswith('[') and pronunciation_text.endswith(']'):
                        # Convert to forward slash notation
                        pronunciation = pronunciation_text.replace('[', '/').replace(']', '/')
                        return pronunciation
                    elif pronunciation_text:
                        # Add forward slashes if not present
                        return f'/{pronunciation_text}/'
        except Exception:
            pass
        return ''
    
    @staticmethod
    def _extract_word_type(word_entry: Tag) -> str:
        """Extract word type (substantiv, verbum, etc.) from the word entry."""
        try:
            # Look for word class information in tekstmedium span
            word_class_span = word_entry.find('span', class_='tekstmedium')
            if word_class_span:
                word_type_text = word_class_span.get_text(strip=True)
                
                # Extract the word type part (before any comma)
                word_type = word_type_text.split(',')[0].strip()
                
                # Clean up and return
                return word_type.lower()
        except Exception:
            pass
        return ''
    
    @staticmethod
    def _extract_gender(word_entry: Tag) -> str:
        """Extract gender information for nouns."""
        try:
            # Look for gender information in the tekstmedium span
            word_class_span = word_entry.find('span', class_='tekstmedium')
            if word_class_span:
                text = word_class_span.get_text(strip=True).lower()
                
                # Check for gender patterns
                if 'fælleskøn' in text:
                    return 'en'
                elif 'intetkøn' in text:
                    return 'et'
                elif 'flertal' in text:
                    return 'plural'
                
                # Look for direct gender indicators
                if ', en' in text or text.endswith(' en'):
                    return 'en'
                elif ', et' in text or text.endswith(' et'):
                    return 'et'
        except Exception:
            pass
        return ''
    
    @staticmethod
    def _extract_plural(word_entry: Tag) -> str:
        """Extract plural form for nouns."""
        try:
            # Look for plural indicators
            inflection_spans = word_entry.find_all('span', class_='tekstmedium')
            for span in inflection_spans:
                text = span.get_text(strip=True)
                # Look for plural patterns
                if 'flertal' in text.lower() or 'pl.' in text.lower():
                    # Extract the plural form
                    plural_match = re.search(r'([a-zæøå]+(?:er|e|ne|ene|s))', text, re.IGNORECASE)
                    if plural_match:
                        return plural_match.group(1)
        except Exception:
            pass
        return ''
    
    @staticmethod
    def _extract_inflections(word_entry: Tag) -> str:
        """Extract inflection information."""
        try:
            inflections = []
            
            # Look for various inflection patterns
            spans = word_entry.find_all('span', class_='tekstmedium')
            for span in spans:
                text = span.get_text(strip=True)
                
                # Skip if it's just gender
                if text.lower() in ['en', 'et']:
                    continue
                
                # Look for verb conjugations
                if any(keyword in text.lower() for keyword in ['datid', 'nutid', 'tillægsform', 'infinitiv']):
                    inflections.append(text)
                
                # Look for adjective forms
                if any(keyword in text.lower() for keyword in ['komparativ', 'superlativ', 'tillægsform']):
                    inflections.append(text)
                
                # Look for noun declensions
                if any(keyword in text.lower() for keyword in ['bestemt', 'ubestemt', 'genitiv']):
                    inflections.append(text)
            
            return ', '.join(inflections) if inflections else ''
        except Exception:
            pass
        return ''
    
    @staticmethod
    def _extract_definition(word_entry: Tag) -> str:
        """Extract Danish definition from the word entry."""
        try:
            # Look for definition text in the definitionIndent div
            definition_indent = word_entry.find('div', class_='definitionIndent')
            if definition_indent:
                # Look for the actual definition span
                definition_span = definition_indent.find('span', class_='definition')
                if definition_span:
                    definition_text = definition_span.get_text(strip=True)
                    
                    # Clean up the definition
                    # Remove extra whitespace
                    definition_text = re.sub(r'\s+', ' ', definition_text).strip()
                    
                    # Ensure it ends with a period
                    if definition_text and not definition_text.endswith('.'):
                        definition_text += '.'
                    
                    return definition_text
                    
                # Fallback: look for any definition content
                definition_box = definition_indent.find('div', class_='definitionBox')
                if definition_box:
                    # Extract text but exclude certain elements
                    for unwanted in definition_box.find_all(['a', 'span'], class_=['kIkon', 'dividerDot', 'dividerSmall', 'stempel']):
                        unwanted.decompose()
                    
                    definition_text = definition_box.get_text(strip=True)
                    
                    # Clean up and take first sentence
                    sentences = definition_text.split('.')
                    if sentences:
                        definition_text = sentences[0].strip()
                        if definition_text:
                            return definition_text + '.'
            
            # Alternative: look for definition in other structures
            parent = word_entry.parent if hasattr(word_entry, 'parent') else word_entry
            definition_spans = parent.find_all('span', class_='definition')
            if definition_spans:
                definition_text = definition_spans[0].get_text(strip=True)
                if definition_text:
                    return definition_text + ('.' if not definition_text.endswith('.') else '')
                
        except Exception:
            pass
        return ''
    
    @staticmethod
    def _extract_english_translation(word_entry: Tag) -> str:
        """Extract English translation if available."""
        try:
            # Look for English translation sections
            # This might be in various places depending on the word
            english_sections = word_entry.find_all('span', class_='translation')
            for section in english_sections:
                text = section.get_text(strip=True)
                if text and any(c.isalpha() and ord(c) < 128 for c in text):
                    # Simple heuristic: if it contains ASCII letters, it might be English
                    return text
                    
            # Alternative: look for parenthetical English translations
            all_text = word_entry.get_text()
            english_match = re.search(r'\(([a-zA-Z\s]+)\)', all_text)
            if english_match:
                potential_english = english_match.group(1).strip()
                # Check if it looks like English (no Danish special characters)
                if not any(c in potential_english for c in 'æøåÆØÅ'):
                    return potential_english
                    
        except Exception:
            pass
        return ''
    
    @staticmethod
    def _extract_audio_url(soup: BeautifulSoup) -> str:
        """Extract audio URL from the page."""
        try:
            # Look for pronunciation section
            udtale_div = soup.find('div', id='id-udt')
            if udtale_div:
                # Find audio fallback links
                audio_links = udtale_div.find_all('a', id=lambda x: x and x.endswith('_fallback'))
                if audio_links:
                    audio_url = audio_links[0].get('href')
                    if audio_url:
                        # Make sure we have a full URL
                        if not audio_url.startswith('http'):
                            from urllib.parse import urljoin
                            audio_url = urljoin('https://ordnet.dk', audio_url)
                        return audio_url
        except Exception:
            pass
        return ''
