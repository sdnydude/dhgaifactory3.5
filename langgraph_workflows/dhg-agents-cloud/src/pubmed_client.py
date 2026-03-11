"""
Shared PubMed E-Utils API client.
=================================
Extracted from research_agent.py for reuse across agents.
Includes build_references_section() for consistent PubMed-backed
AMA reference generation across all content agents.
"""

import re
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Tuple

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


# ---------------------------------------------------------------------------
# Shared reference-section builder
# ---------------------------------------------------------------------------

_STOP_WORDS = frozenset({
    "This", "That", "These", "Those", "There", "They", "With",
    "From", "About", "Into", "Over", "After", "Before", "During",
    "Between", "Through", "Under", "While", "Where", "When", "Each",
    "Many", "Most", "Some", "Such", "Only", "Also", "However",
})


def _extract_keywords(context_text: str) -> List[str]:
    """Extract medical keywords from a citation context sentence.

    Prioritises named trials (DAPA-CKD), drug names (-flozin, -glutide),
    and capitalised medical terms over generic prose.
    """
    # Named trials / acronyms (DAPA-CKD, EMPEROR-Preserved, SGLT2, etc.)
    trials = re.findall(r'[A-Z][A-Z0-9\-]{2,}(?:\-[A-Z][a-z]+)?', context_text)
    # Drug names by suffix
    drugs = re.findall(
        r'\b\w+(?:mab|nib|lib|zumab|flozin|sartan|pril|olol|statin|tide|glutide)\b',
        context_text, re.IGNORECASE,
    )
    keywords = list(dict.fromkeys(trials + drugs))  # deduplicate, preserve order
    if keywords:
        return keywords[:4]

    # Fallback: capitalised medical terms minus stop words
    medical_terms = [
        t for t in re.findall(r'\b[A-Z][a-z]{3,}\b', context_text)
        if t not in _STOP_WORDS
    ]
    return medical_terms[:5]


def _extract_citation_contexts(document: str) -> Dict[int, List[str]]:
    """Parse inline [N] citations from a document and return context per number."""
    citation_contexts: Dict[int, List[str]] = {}
    sentences = re.split(r'(?<=[.!?])\s+', document)

    for sentence in sentences:
        nums_in_sentence = re.findall(r'\[(\d+)\]', sentence)
        for num_str in nums_in_sentence:
            num = int(num_str)
            clean = re.sub(r'\[\d+\]', '', sentence).strip()
            clean = re.sub(r'^#{1,3}\s+.*$', '', clean, flags=re.MULTILINE).strip()
            if clean and len(clean) > 20:
                if num not in citation_contexts:
                    citation_contexts[num] = []
                citation_contexts[num].append(clean)
    return citation_contexts


async def build_references_section(document: str, disease_state: str) -> Tuple[str, int, int]:
    """Build a PubMed-verified AMA references section for a document.

    Args:
        document: The full document text containing inline [N] citations.
        disease_state: The medical topic for PubMed search context.

    Returns:
        Tuple of (references_text, verified_count, unverified_count).
        references_text includes the "## References" header.
    """
    citation_contexts = _extract_citation_contexts(document)

    if not citation_contexts:
        return "\n\n## References\n\n[No inline citations found in document]", 0, 0

    pubmed = PubMedClient()
    verified_refs: List[Tuple[int, str]] = []
    unverified_refs: List[Tuple[int, str]] = []
    used_pmids: set = set()

    for num in sorted(citation_contexts.keys()):
        contexts = citation_contexts[num]
        keywords = _extract_keywords(contexts[0])
        query = f"{disease_state} {' '.join(keywords)}" if keywords else disease_state

        found = False
        try:
            pmids = await pubmed.search(query, max_results=5, years=10)
            fresh_pmids = [p for p in pmids if p not in used_pmids]
            if fresh_pmids:
                articles = await pubmed.fetch_details(fresh_pmids[:1])
                if articles:
                    article = articles[0]
                    used_pmids.add(article["pmid"])
                    verified_refs.append((num, pubmed.format_ama(article)))
                    found = True
        except Exception:
            pass

        if not found:
            unverified_refs.append((num, contexts[0][:100]))

    ref_lines = []
    for num, citation in sorted(verified_refs, key=lambda x: x[0]):
        ref_lines.append(f"{num}. {citation}")

    if unverified_refs:
        ref_lines.append("")
        ref_lines.append("*The following citations could not be verified against PubMed:*")
        for num, desc in sorted(unverified_refs, key=lambda x: x[0]):
            ref_lines.append(f"{num}. [UNVERIFIED] {desc}")

    references_text = "\n\n## References\n\n" + "\n".join(ref_lines)
    return references_text, len(verified_refs), len(unverified_refs)
