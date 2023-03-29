import logging
from typing import Dict, List, Optional
from beacon.db.filters import apply_alphanumeric_filter, apply_filters
from beacon.db.schemas import DefaultSchemas
from beacon.db.utils import query_id, query_ids, get_count, get_documents, get_cross_query, get_cross_query_variants
from beacon.request.model import AlphanumericFilter, Operator, RequestParams
from beacon.db import client
import json
from bson import json_util

LOG = logging.getLogger(__name__)

VARIANTS_PROPERTY_MAP = {
    "assemblyId": "_position.assemblyId",
    "Chromosome": "_position.refseqId",
    "start": "_position.start",
    "end": "_position.end",
    "referenceBases": "variation.referenceBases",
    "alternateBases": "variation.alternateBases",
    "variantType": "variation.variantType",
    "variantMinLength": None,
    "variantMaxLength": None,
    "mateName": None,
    "gene": "molecularAttributes.geneIds",
    "aachange": "molecularAttributes.aminoacidChanges"
}

def include_resultset_responses(query: Dict[str, List[dict]], qparams: RequestParams):
    LOG.debug("Include Resultset Responses = {}".format(qparams.query.include_resultset_responses))
    include = qparams.query.include_resultset_responses
    if include == 'HIT':
        query = query
    elif include == 'ALL':
        query = {}
    elif include == 'NONE':
        query = {'$text': {'$search': '########'}}
    else:
        query = query
    return query


def generate_position_filter_start(key: str, value: List[int]) -> List[AlphanumericFilter]:
    LOG.debug("len value = {}".format(len(value)))
    filters = []
    if len(value) == 1:
        filters.append(AlphanumericFilter(
            id=VARIANTS_PROPERTY_MAP[key],
            value=[value[0]],
            operator=Operator.GREATER_EQUAL
        ))
    elif len(value) == 2:
        filters.append(AlphanumericFilter(
            id=VARIANTS_PROPERTY_MAP[key],
            value=[value[0]],
            operator=Operator.GREATER_EQUAL
        ))
        filters.append(AlphanumericFilter(
            id=VARIANTS_PROPERTY_MAP[key],
            value=[value[1]],
            operator=Operator.LESS_EQUAL
        ))
    return filters


def generate_position_filter_end(key: str, value: List[int]) -> List[AlphanumericFilter]:
    LOG.debug("len value = {}".format(len(value)))
    filters = []
    if len(value) == 1:
        filters.append(AlphanumericFilter(
            id=VARIANTS_PROPERTY_MAP[key],
            value=[value[0]],
            operator=Operator.LESS_EQUAL
        ))
    elif len(value) == 2:
        filters.append(AlphanumericFilter(
            id=VARIANTS_PROPERTY_MAP[key],
            value=[value[0]],
            operator=Operator.GREATER_EQUAL
        ))
        filters.append(AlphanumericFilter(
            id=VARIANTS_PROPERTY_MAP[key],
            value=[value[1]],
            operator=Operator.LESS_EQUAL
        ))
    return filters


def apply_request_parameters(query: Dict[str, List[dict]], qparams: RequestParams):
    collection = 'g_variants'
    LOG.debug("Request parameters len = {}".format(len(qparams.query.request_parameters)))
    if len(qparams.query.request_parameters) > 0 and "$and" not in query:
        query["$and"] = []
    for k, v in qparams.query.request_parameters.items():
        if k == "start":
            if isinstance(v, str):
                v = v.split(',')
            filters = generate_position_filter_start(k, v)
            for filter in filters:
                query["$and"].append(apply_alphanumeric_filter({}, filter, collection))
        elif k == "end":
            if isinstance(v, str):
                v = v.split(',')
            filters = generate_position_filter_end(k, v)
            for filter in filters:
                query["$and"].append(apply_alphanumeric_filter({}, filter, collection))
        elif k == "variantMinLength" or k == "variantMaxLength" or k == "mateName":
            continue
        else:
            query["$and"].append(apply_alphanumeric_filter({}, AlphanumericFilter(
                id=VARIANTS_PROPERTY_MAP[k],
                value=v
            ), collection))
    return query


def get_variants(entry_id: Optional[str], qparams: RequestParams, allowed_ids: list):
    collection = 'g_variants'
    query = apply_request_parameters({}, qparams)
    query = apply_filters(query, qparams.query.filters, collection, allowed_ids)
    query = include_resultset_responses(query, qparams)
    schema = DefaultSchemas.GENOMICVARIATIONS
    count = get_count(client.beacon.genomicVariations, query)
    include = qparams.query.include_resultset_responses
    if include == 'MISS':
        pre_docs = get_documents(
            client.beacon.genomicVariations,
            query,
            qparams.query.pagination.skip,
            count
        )
        negative_query={}
        ids_array = []
        for doc in pre_docs:
            elem_query={}
            elem_query['_id']=doc['_id']
            ids_array.append(elem_query)
        
        negative_query['$nor']=ids_array
        LOG.debug(negative_query)
        docs = get_documents(
            client.beacon.genomicVariations,
            negative_query,
            qparams.query.pagination.skip,
            qparams.query.pagination.limit
        )
        count = get_count(client.beacon.genomicVariations, negative_query)
    else:
        docs = get_documents(
            client.beacon.genomicVariations,
            query,
            qparams.query.pagination.skip,
            qparams.query.pagination.limit
        )
    return schema, count, docs


def get_variant_with_id(entry_id: Optional[str], qparams: RequestParams, allowed_ids: list):
    collection = 'g_variants'
    query = {"$and": [{"variantInternalId": entry_id}]}
    query = apply_request_parameters(query, qparams)
    query = apply_filters(query, qparams.query.filters, collection, allowed_ids)
    query = include_resultset_responses(query, qparams)
    schema = DefaultSchemas.GENOMICVARIATIONS
    count = get_count(client.beacon.genomicVariations, query)
    include = qparams.query.include_resultset_responses
    if include == 'MISS':
        pre_docs = get_documents(
            client.beacon.genomicVariations,
            query,
            qparams.query.pagination.skip,
            count
        )
        negative_query={}
        ids_array = []
        for doc in pre_docs:
            elem_query={}
            elem_query['_id']=doc['_id']
            ids_array.append(elem_query)
        
        negative_query['$nor']=ids_array
        LOG.debug(negative_query)
        docs = get_documents(
            client.beacon.genomicVariations,
            negative_query,
            qparams.query.pagination.skip,
            qparams.query.pagination.limit
        )
        count = get_count(client.beacon.genomicVariations, negative_query)
    else:
        docs = get_documents(
            client.beacon.genomicVariations,
            query,
            qparams.query.pagination.skip,
            qparams.query.pagination.limit
        )
    return schema, count, docs


def get_biosamples_of_variant(entry_id: Optional[str], qparams: RequestParams, allowed_ids: list):
    collection = 'g_variants'
    query = {"$and": [{"variantInternalId": entry_id}]}
    query = apply_request_parameters(query, qparams)
    query = apply_filters(query, qparams.query.filters, collection, allowed_ids)
    count = get_count(client.beacon.genomicVariations, query)
    biosample_ids = client.beacon.genomicVariations \
        .find_one(query, {"caseLevelData.biosampleId": 1, "_id": 0})
    
    biosample_ids=get_cross_query_variants(biosample_ids,'biosampleId','id')
    query = query = apply_filters(query, qparams.query.filters, collection, allowed_ids)

    query = include_resultset_responses(query, qparams)
    schema = DefaultSchemas.BIOSAMPLES
    include = qparams.query.include_resultset_responses
    if include == 'MISS':
        pre_docs = get_documents(
            client.beacon.biosamples,
            query,
            qparams.query.pagination.skip,
            count
        )
        negative_query={}
        ids_array = []
        for doc in pre_docs:
            elem_query={}
            elem_query['_id']=doc['_id']
            ids_array.append(elem_query)
        
        negative_query['$nor']=ids_array
        LOG.debug(negative_query)
        docs = get_documents(
            client.beacon.biosamples,
            negative_query,
            qparams.query.pagination.skip,
            qparams.query.pagination.limit
        )
        count = get_count(client.beacon.biosamples, negative_query)
    else:
        docs = get_documents(
            client.beacon.biosamples,
            query,
            qparams.query.pagination.skip,
            qparams.query.pagination.limit
        )
    return schema, count, docs


def get_individuals_of_variant(entry_id: Optional[str], qparams: RequestParams, allowed_ids: list):
    collection = 'g_variants'
    query = {"$and": [{"variantInternalId": entry_id}]}
    query = apply_request_parameters(query, qparams)
    query = query = apply_filters(query, qparams.query.filters, collection, allowed_ids)
    count = get_count(client.beacon.genomicVariations, query)
    individual_ids = client.beacon.genomicVariations \
        .find_one(query, {"caseLevelData.biosampleId": 1, "_id": 0})

    individual_ids = get_cross_query_variants(individual_ids,'biosampleId','id')
    query = query = apply_filters(query, qparams.query.filters, collection, allowed_ids)

    query = include_resultset_responses(query, qparams)
    schema = DefaultSchemas.INDIVIDUALS
    count = get_count(client.beacon.individuals, query)
    include = qparams.query.include_resultset_responses
    if include == 'MISS':
        pre_docs = get_documents(
            client.beacon.individuals,
            query,
            qparams.query.pagination.skip,
            count
        )
        negative_query={}
        ids_array = []
        for doc in pre_docs:
            elem_query={}
            elem_query['_id']=doc['_id']
            ids_array.append(elem_query)
        
        negative_query['$nor']=ids_array
        LOG.debug(negative_query)
        docs = get_documents(
            client.beacon.individuals,
            negative_query,
            qparams.query.pagination.skip,
            qparams.query.pagination.limit
        )
        count = get_count(client.beacon.individuals, negative_query)
    else:
        docs = get_documents(
            client.beacon.individuals,
            query,
            qparams.query.pagination.skip,
            qparams.query.pagination.limit
        )
    return schema, count, docs


def get_runs_of_variant(entry_id: Optional[str], qparams: RequestParams, allowed_ids: list):
    collection = 'g_variants'
    query = {"$and": [{"variantInternalId": entry_id}]}
    query = apply_request_parameters(query, qparams)
    query = query = apply_filters(query, qparams.query.filters, collection, allowed_ids)
    count = get_count(client.beacon.genomicVariations, query)
    run_ids = client.beacon.genomicVariations \
        .find_one(query, {"caseLevelData.biosampleId": 1, "_id": 0})
    
    run_ids=get_cross_query_variants(run_ids,'biosampleId','biosampleId')
    query = query = apply_filters(query, qparams.query.filters, collection, allowed_ids)
    query = include_resultset_responses(query, qparams)
    schema = DefaultSchemas.RUNS
    count = get_count(client.beacon.runs, query)
    include = qparams.query.include_resultset_responses
    if include == 'MISS':
        pre_docs = get_documents(
            client.beacon.runs,
            query,
            qparams.query.pagination.skip,
            count
        )
        negative_query={}
        ids_array = []
        for doc in pre_docs:
            elem_query={}
            elem_query['_id']=doc['_id']
            ids_array.append(elem_query)
        
        negative_query['$nor']=ids_array
        LOG.debug(negative_query)
        docs = get_documents(
            client.beacon.runs,
            negative_query,
            qparams.query.pagination.skip,
            qparams.query.pagination.limit
        )
        count = get_count(client.beacon.runs, negative_query)
    else:
        docs = get_documents(
            client.beacon.runs,
            query,
            qparams.query.pagination.skip,
            qparams.query.pagination.limit
        )
    return schema, count, docs


def get_analyses_of_variant(entry_id: Optional[str], qparams: RequestParams, allowed_ids: list):
    collection = 'g_variants'
    query = {"$and": [{"variantInternalId": entry_id}]}
    query = apply_request_parameters(query, qparams)
    query = query = apply_filters(query, qparams.query.filters, collection, allowed_ids)
    count = get_count(client.beacon.genomicVariations, query)
    analysis_ids = client.beacon.genomicVariations \
        .find_one(query, {"caseLevelData.biosampleId": 1, "_id": 0})

    analysis_ids=get_cross_query_variants(analysis_ids,'biosampleId','biosampleId')
    query = query = apply_filters(query, qparams.query.filters, collection, allowed_ids)
    query = include_resultset_responses(query, qparams)
    schema = DefaultSchemas.ANALYSES
    count = get_count(client.beacon.analyses, query)
    include = qparams.query.include_resultset_responses
    if include == 'MISS':
        pre_docs = get_documents(
            client.beacon.analyses,
            query,
            qparams.query.pagination.skip,
            count
        )
        negative_query={}
        ids_array = []
        for doc in pre_docs:
            elem_query={}
            elem_query['_id']=doc['_id']
            ids_array.append(elem_query)
        
        negative_query['$nor']=ids_array
        LOG.debug(negative_query)
        docs = get_documents(
            client.beacon.analyses,
            negative_query,
            qparams.query.pagination.skip,
            qparams.query.pagination.limit
        )
        count = get_count(client.beacon.analyses, negative_query)
    else:
        docs = get_documents(
            client.beacon.analyses,
            query,
            qparams.query.pagination.skip,
            qparams.query.pagination.limit
        )
    return schema, count, docs

def get_filtering_terms_of_genomicvariation(entry_id: Optional[str], qparams: RequestParams):
    query = {'collection': 'genomicVariations'}
    schema = DefaultSchemas.FILTERINGTERMS
    count = get_count(client.beacon.filtering_terms, query)
    docs = get_documents(
        client.beacon.filtering_terms,
        query,
        qparams.query.pagination.skip,
        qparams.query.pagination.limit
    )
    return schema, count, docs