"""
Script d'extraction de liens web avec filtrage par mois
Auteur: [Votre Nom]
Version: 1.0
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import time
import logging
from typing import List, Set
import sys

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extraction_liens.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class LinkExtractor:
    """
    Classe pour extraire et filtrer les liens d'un site web
    """
    
    # Extensions de fichiers à exclure
    EXCLUDED_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.zip', 
                          '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                          '.mp4', '.avi', '.mov', '.mp3', '.wav']
    
    # Mois cibles avec leurs patterns
    TARGET_MONTHS = {
        'janvier': ['01', '1', 'janvier', 'january'],
        'février': ['02', '2', 'février', 'february'],
        'mars': ['03', '3', 'mars', 'march'],
        'novembre': ['11', 'novembre', 'november'],
        'décembre': ['12', 'décembre', 'december']
    }

    def __init__(self, base_url: str, delay: float = 0.5):
        """
        Initialise l'extracteur de liens
        
        Args:
            base_url: URL de base du site à analyser
            delay: Délai entre les requêtes (en secondes)
        """
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def get_all_domain_links(self) -> List[str]:
        """
        Récupère tous les liens d'un domaine sans limitation
        
        Returns:
            Liste de tous les liens uniques trouvés
        """
        visited: Set[str] = set()
        to_visit: List[str] = [self.base_url]
        all_links: Set[str] = set()
        page_count = 0

        logger.info(f"Début de l'extraction pour le domaine: {self.domain}")

        while to_visit:
            current_url = to_visit.pop(0)

            if current_url in visited:
                continue

            try:
                logger.info(f"Page {page_count + 1}: {current_url}")
                response = self.session.get(current_url, timeout=15)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, 'html.parser')
                visited.add(current_url)
                page_count += 1

                # Récupérer tous les liens de la page
                new_links = self._extract_links_from_page(soup, current_url)
                all_links.update(new_links)

                # Ajouter les nouveaux liens à visiter
                for link in new_links:
                    if (link not in visited and 
                        link not in to_visit and 
                        self._should_visit_link(link)):
                        to_visit.append(link)

                time.sleep(self.delay)

            except requests.RequestException as e:
                logger.warning(f"Erreur avec {current_url}: {e}")
                continue

        logger.info(f"Extraction terminée. {page_count} pages visitées, {len(all_links)} liens trouvés.")
        return list(all_links)

    def _extract_links_from_page(self, soup: BeautifulSoup, current_url: str) -> Set[str]:
        """
        Extrait tous les liens d'une page HTML
        
        Args:
            soup: Objet BeautifulSoup de la page
            current_url: URL actuelle pour résoudre les liens relatifs
            
        Returns:
            Ensemble de liens absolus
        """
        links = set()
        for link in soup.find_all('a', href=True):
            href = link['href'].strip()
            if href and not href.startswith(('javascript:', 'mailto:', 'tel:')):
                absolute_url = urljoin(current_url, href)
                if urlparse(absolute_url).netloc == self.domain:
                    links.add(absolute_url)
        return links

    def _should_visit_link(self, url: str) -> bool:
        """
        Détermine si un lien devrait être visité
        
        Args:
            url: URL à vérifier
            
        Returns:
            True si le lien devrait être visité
        """
        # Exclure les fichiers
        if any(url.lower().endswith(ext) for ext in self.EXCLUDED_EXTENSIONS):
            return False
        
        # Exclure les anchors et URLs avec fragments
        if '#' in url.split('?')[0]:
            return False
            
        return True

    def filter_links_by_months(self, links: List[str]) -> List[str]:
        """
        Filtre les liens contenant les mois cibles
        
        Args:
            links: Liste de liens à filtrer
            
        Returns:
            Liste de liens filtrés
        """
        filtered_links = [link for link in links if self._contains_target_month(link)]
        return filtered_links

    def _contains_target_month(self, url: str) -> bool:
        """
        Vérifie si l'URL contient un des mois cibles
        
        Args:
            url: URL à vérifier
            
        Returns:
            True si l'URL contient un mois cible
        """
        url_lower = url.lower()
        
        # Patterns regex pour les formats date
        date_patterns = [
            r'/(\d{4})/(0?[1-3]|11|12)/',  # Format YYYY/MM/
            r'/(\d{4})-(0?[1-3]|11|12)-',  # Format YYYY-MM-
            r'(\d{4})/(0?[1-3]|11|12)/',   # Format sans slash initial
            r'(\d{4})-(0?[1-3]|11|12)-'    # Format sans slash initial
        ]
        
        # Vérifier les patterns regex
        for pattern in date_patterns:
            if re.search(pattern, url):
                return True
        
        # Vérifier les noms de mois
        for month_patterns in self.TARGET_MONTHS.values():
            for pattern in month_patterns:
                if pattern in url_lower:
                    return True
        
        return False

    def get_month_statistics(self, filtered_links: List[str]) -> dict:
        """
        Génère des statistiques par mois
        
        Args:
            filtered_links: Liste de liens filtrés
            
        Returns:
            Dictionnaire avec les statistiques par mois
        """
        stats = {month: 0 for month in self.TARGET_MONTHS.keys()}
        
        for link in filtered_links:
            for month_name, patterns in self.TARGET_MONTHS.items():
                for pattern in patterns:
                    if pattern in link.lower():
                        stats[month_name] += 1
                        break
        
        return stats

    def save_links_to_file(self, links: List[str], filename: str = "liens_filtres.txt"):
        """
        Sauvegarde les liens dans un fichier texte
        
        Args:
            links: Liste de liens à sauvegarder
            filename: Nom du fichier de sortie
        """
        try:
            with open(filename, 'w', encoding='utf-8') as file:
                for link in sorted(links):
                    file.write(link + '\n')
            logger.info(f"✅ {len(links)} liens sauvegardés dans {filename}")
        except IOError as e:
            logger.error(f"❌ Erreur lors de la sauvegarde: {e}")

def main():
    """
    Fonction principale
    """
    # Configuration
    website_url = "https://afri-carrieres.com/"
    output_filename = "liens_filtres.txt"
    
    try:
        # Initialisation
        extractor = LinkExtractor(website_url, delay=0.5)
        
        # Extraction des liens
        logger.info("🚀 Début de l'extraction complète...")
        all_links = extractor.get_all_domain_links()
        
        # Filtrage par mois
        filtered_links = extractor.filter_links_by_months(all_links)
        
        # Affichage des résultats
        logger.info(f"📊 Résultats de l'extraction:")
        logger.info(f"   - Total des liens trouvés: {len(all_links)}")
        logger.info(f"   - Liens filtrés: {len(filtered_links)}")
        
        if filtered_links:
            # Sauvegarde
            extractor.save_links_to_file(filtered_links, output_filename)
            
            # Statistiques
            stats = extractor.get_month_statistics(filtered_links)
            logger.info("📈 Statistiques par mois:")
            for month, count in stats.items():
                logger.info(f"   - {month.capitalize()}: {count} liens")
            
            # Exemples
            logger.info("📝 Exemples de liens sauvegardés:")
            for i, link in enumerate(filtered_links[:10], 1):
                logger.info(f"   {i}. {link}")
        else:
            logger.warning("❌ Aucun lien ne correspond aux critères des mois spécifiés")
            
    except KeyboardInterrupt:
        logger.info("⏹️ Extraction interrompue par l'utilisateur")
    except Exception as e:
        logger.error(f"💥 Erreur critique: {e}")

if __name__ == "__main__":
    main()
