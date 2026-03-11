"""
Shared PubMed E-Utils API client.
=================================
Extracted from research_agent.py for reuse across agents.
"""

import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict

from langsmith import traceable


class PubMedClient:
    """PubMed E-Utils API client."""

    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    @traceable(name="pubmed_search", run_type="retriever")
    async def search(self, query: str, max_results: int = 50, years: int = 5) -> List[str]:
        """Search PubMed and return PMIDs."""
        min_date = f"{datetime.now().year - years}/01/01"
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "mindate": min_date,
            "datetype": "pdat",
            "retmode": "json",
            "sort": "relevance",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.BASE_URL}/esearch.fcgi", params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("esearchresult", {}).get("idlist", [])

    @traceable(name="pubmed_fetch", run_type="retriever")
    async def fetch_details(self, pmids: List[str]) -> List[Dict]:
        """Fetch article details for PMIDs."""
        if not pmids:
            return []

        params = {
            "db": "pubmed",
            "id": ",".join(pmids[:50]),
            "retmode": "xml",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(f"{self.BASE_URL}/efetch.fcgi", params=params)
            response.raise_for_status()
            return self._parse_xml(response.text)

    def _parse_xml(self, xml_text: str) -> List[Dict]:
        """Parse PubMed XML response."""
        articles = []

        try:
            root = ET.fromstring(xml_text)
            for article in root.findall(".//PubmedArticle"):
                try:
                    medline = article.find(".//MedlineCitation")
                    if medline is None:
                        continue

                    pmid = medline.findtext("PMID", "")
                    art = medline.find(".//Article")
                    if art is None:
                        continue

                    title = art.findtext(".//ArticleTitle", "")
                    abstract_parts = [el.text or "" for el in art.findall(".//AbstractText")]
                    abstract = " ".join(abstract_parts)

                    journal_el = art.find(".//Journal")
                    journal = journal_el.findtext(".//Title", "") if journal_el else ""
                    journal_abbrev = ""
                    if journal_el is not None:
                        iso_abbrev = journal_el.findtext(".//ISOAbbreviation", "")
                        journal_abbrev = iso_abbrev if iso_abbrev else journal

                    year = ""
                    pub_date = journal_el.find(".//PubDate") if journal_el else None
                    if pub_date is not None:
                        year = pub_date.findtext("Year", "")

                    volume = ""
                    issue = ""
                    pages = ""
                    ji = art.find(".//Journal/JournalIssue")
                    if ji is not None:
                        volume = ji.findtext("Volume", "")
                        issue = ji.findtext("Issue", "")
                    pages = art.findtext(".//Pagination/MedlinePgn", "")

                    authors = []
                    for author in art.findall(".//Author"):
                        last = author.findtext("LastName", "")
                        init = author.findtext("Initials", "")
                        if last:
                            authors.append(f"{last} {init}".strip())

                    doi = ""
                    for eid in article.findall(".//ArticleId"):
                        if eid.get("IdType") == "doi":
                            doi = eid.text or ""
                            break

                    pub_types = [pt.text for pt in medline.findall(".//PublicationType") if pt.text]

                    articles.append({
                        "pmid": pmid,
                        "doi": doi,
                        "title": title,
                        "authors": authors,
                        "journal": journal,
                        "journal_abbrev": journal_abbrev,
                        "year": int(year) if year.isdigit() else 0,
                        "volume": volume,
                        "issue": issue,
                        "pages": pages,
                        "abstract": abstract[:1000],
                        "publication_types": pub_types,
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    })
                except Exception:
                    continue
        except Exception:
            pass

        return articles

    def format_ama(self, article: Dict) -> str:
        """Format a single article in AMA citation style."""
        authors = article.get("authors", [])
        if len(authors) > 6:
            author_str = ", ".join(authors[:6]) + ", et al"
        else:
            author_str = ", ".join(authors)

        title = article.get("title", "").rstrip(".")
        journal = article.get("journal_abbrev", "") or article.get("journal", "")
        year = article.get("year", "")
        vol = article.get("volume", "")
        issue = article.get("issue", "")
        pages = article.get("pages", "")
        doi = article.get("doi", "")
        url = article.get("url", "")

        citation = f"{author_str}. {title}. {journal}. {year}"
        if vol:
            citation += f";{vol}"
            if issue:
                citation += f"({issue})"
        if pages:
            citation += f":{pages}"
        citation += "."
        if doi:
            citation += f" doi:{doi}"
        if url:
            citation += f" {url}"

        return citation
