"""
Command line interface for literature extraction
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import List

# Add the scripts directory to sys.path to import modules
scripts_dir = Path(__file__).parent.parent.parent
sys.path.append(str(scripts_dir))

from db.database import get_db
from .extractor import LiteratureExtractor
from .config import LOG_FORMAT, LOG_LEVEL

# Set up logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)
log = logging.getLogger(__name__)


async def extract_disease_literature_cli(diseases: List[str]) -> None:
    """Extract literature for diseases via CLI"""
    db_session = next(get_db())
    
    try:
        extractor = LiteratureExtractor(db_session)
        
        if len(diseases) == 1:
            # Single disease
            disease = diseases[0]
            log.info(f"Starting extraction for disease: {disease}")
            success = await extractor.extract_literature_for_disease(disease)
            
            if success:
                summary = extractor.get_extraction_summary(disease)
                print(f"\n✓ Extraction completed for {disease}")
                print(f"  Articles stored: {summary['total_articles']}")
                print(f"  With full text: {summary['articles_with_full_text']} ({summary['full_text_percentage']}%)")
            else:
                print(f"\n✗ Extraction failed for {disease}")
                
        else:
            # Multiple diseases
            log.info(f"Starting batch extraction for {len(diseases)} diseases")
            results = await extractor.extract_literature_batch(diseases)
            
            successful = sum(1 for success in results.values() if success)
            print(f"\n✓ Batch extraction completed: {successful}/{len(diseases)} successful")
            
            for disease, success in results.items():
                if success:
                    summary = extractor.get_extraction_summary(disease)
                    print(f"  ✓ {disease}: {summary['total_articles']} articles ({summary['full_text_percentage']}% with full text)")
                else:
                    print(f"  ✗ {disease}: Failed")
    
    finally:
        db_session.close()


async def extract_target_literature_cli(target: str, diseases: List[str]) -> None:
    """Extract literature for target-disease combinations via CLI"""
    db_session = next(get_db())
    
    try:
        extractor = LiteratureExtractor(db_session)
        
        if len(diseases) == 1:
            # Single target-disease combination
            disease = diseases[0] if diseases[0] != "no-disease" else None
            log.info(f"Starting extraction for target-disease: {target}-{diseases[0]}")
            success = await extractor.extract_literature_for_disease(disease, target)
            
            if success:
                summary = extractor.get_extraction_summary(disease, target)
                print(f"\n✓ Extraction completed for {target}-{diseases[0]}")
                print(f"  Articles stored: {summary['total_articles']}")
                print(f"  With full text: {summary['articles_with_full_text']} ({summary['full_text_percentage']}%)")
            else:
                print(f"\n✗ Extraction failed for {target}-{diseases[0]}")
                
        else:
            # Multiple target-disease combinations
            log.info(f"Starting batch extraction for {target} with {len(diseases)} diseases")
            results = {}
            
            for disease in diseases:
                disease_param = disease if disease != "no-disease" else None
                success = await extractor.extract_literature_for_disease(disease_param, target)
                results[f"{target}-{disease}"] = success
            
            successful = sum(1 for success in results.values() if success)
            print(f"\n✓ Batch extraction completed: {successful}/{len(diseases)} successful")
            
            for combo, success in results.items():
                if success:
                    disease_name = combo.split('-', 1)[1]
                    disease_param = disease_name if disease_name != "no-disease" else None
                    summary = extractor.get_extraction_summary(disease_param, target)
                    print(f"  ✓ {combo}: {summary['total_articles']} articles ({summary['full_text_percentage']}% with full text)")
                else:
                    print(f"  ✗ {combo}: Failed")
    
    finally:
        db_session.close()


async def show_summary_cli(diseases: List[str], target: str = None) -> None:
    """Show extraction summary via CLI"""
    db_session = next(get_db())
    
    try:
        extractor = LiteratureExtractor(db_session)
        
        print(f"\n{'='*60}")
        print("LITERATURE EXTRACTION SUMMARY")
        print(f"{'='*60}")
        
        for disease in diseases:
            disease_param = disease if disease != "no-disease" else None
            summary = extractor.get_extraction_summary(disease_param, target)
            
            combo_name = f"{target}-{disease}" if target else disease
            print(f"\n{combo_name}:")
            print(f"  Total articles: {summary['total_articles']}")
            print(f"  With full text: {summary['articles_with_full_text']} ({summary['full_text_percentage']}%)")
            print(f"  With PMCID: {summary['articles_with_pmcid']} ({summary['pmcid_percentage']}%)")
    
    finally:
        db_session.close()


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Literature Extraction CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract literature for a single disease
  python cli.py extract-disease "alzheimer disease"
  
  # Extract literature for multiple diseases  
  python cli.py extract-disease "alzheimer disease" "parkinson disease"
  
  # Extract literature for target-disease combination
  python cli.py extract-target APOE "alzheimer disease"
  
  # Extract literature for target only
  python cli.py extract-target APOE "no-disease"
  
  # Show summary
  python cli.py summary "alzheimer disease" "parkinson disease"
  
  # Show summary for target-disease
  python cli.py summary --target APOE "alzheimer disease"
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Extract disease literature
    extract_disease_parser = subparsers.add_parser(
        'extract-disease',
        help='Extract literature for diseases'
    )
    extract_disease_parser.add_argument(
        'diseases',
        nargs='+',
        help='Disease names'
    )
    
    # Extract target literature
    extract_target_parser = subparsers.add_parser(
        'extract-target', 
        help='Extract literature for target-disease combinations'
    )
    extract_target_parser.add_argument(
        'target',
        help='Target name'
    )
    extract_target_parser.add_argument(
        'diseases',
        nargs='+',
        help='Disease names (use "no-disease" for target-only)'
    )
    
    # Show summary
    summary_parser = subparsers.add_parser(
        'summary',
        help='Show extraction summary'
    )
    summary_parser.add_argument(
        'diseases',
        nargs='+',
        help='Disease names'
    )
    summary_parser.add_argument(
        '--target',
        help='Target name (optional)'
    )
    
    # Logging level
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Run appropriate command
    try:
        if args.command == 'extract-disease':
            asyncio.run(extract_disease_literature_cli(args.diseases))
        elif args.command == 'extract-target':
            asyncio.run(extract_target_literature_cli(args.target, args.diseases))
        elif args.command == 'summary':
            asyncio.run(show_summary_cli(args.diseases, args.target))
        else:
            parser.print_help()
    
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        log.error(f"CLI error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()