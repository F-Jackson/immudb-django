from datetime import timedelta
import json
from typing import Dict
from django.conf import settings
from django.db import models
from django.utils.timezone import now
from abc import ABC
from django.utils.crypto import get_random_string
import random

from immudb_connection.connection import starting_db
from immudb.datatypes import DeleteKeysRequest


NOT_FIELDS_VALUES = ['immu_confs', 'id', 'uuid', 'verified']

immu_client = starting_db(user='immudb', password='immudb')

def random_uuid():
    random_str = get_random_string(length=random.randint(10, 255))
    immu_obj = immu_client.get(random_str.encode())
    
    if immu_obj is not None:
        return random_uuid()

    return random_str

class ImmudbKeyField(models.Model):
    nome = models.CharField(max_length=155)
    ok = models.IntegerField()
    
    # DONT TOUCH
    verified = models.BooleanField(default=False)
    uuid = models.CharField(max_length=255, default=random_uuid())
    
    # ABC VARS
    immu_confs = {
        'expireableDateTime': settings.IMMU_DEFAULT_EXPIRE_TIME,
    }
    
    class Meta:
        """
            Setting the abc class for only interact with the immu database
        """
        abstract = True
        managed = False
        
    
    def save(self, *args, **kwargs) -> dict:
        """
            save the model inside the immu datase
        """
        
        # MODEL FIELD VALUES
        values = {}
        
        # GET ALL THE FIELDS GIVEN BY THE USER INSIDE THE MODEL EXECEPT THE FIELDS THAT ARE NECESSARY FOR THE ABC CLASS WORK
        for field in self.__class__._meta.fields:
            if field.name not in NOT_FIELDS_VALUES:
                value = getattr(self, field.name)
                values[field.name] = str(value)
                
        # PREPARE ALL THE DATA FOR CREATION
        json_values = json.dumps(values).encode()
        uuid_pk = self.uuid.encode()
                
        # SAVING THE MODEL INSIDE THE IMMU DATABASE
        if self.immu_confs['expireableDateTime'] is not None:
            expireTime = now() + timedelta(**self.immu_confs['expireableDateTime'])
            
            immu_client.expireableSet(uuid_pk, json_values, expireTime)
        elif self.verified:
            immu_client.verifiedSet(uuid_pk, json_values)
        else:
            immu_client.set(uuid_pk, json_values)
        
        
    @classmethod
    def create(cls, *, 
               uuid: str | None = None, verified: bool = False, 
               refs: list[str] | None = None, 
               refs_scores: Dict[str, float] | None = None,
               **kwargs) -> dict:
        """
            Creates an object inside the immu database
        """
        
        # CREATE OBJECT ON IMMU DATABASE
        cls.objects.create(uuid=uuid, verified=verified,**kwargs)
        
        # SET REFS
        if refs is not None:
            if verified:
                for ref in refs:
                    immu_client.verifiedSetReference(uuid.encode(), ref.encode())
            else:
                for ref in refs:
                    immu_client.setReference(uuid.encode(), ref.encode())
        
        # SET ZSCORES
        if refs_scores is not None:
            if verified:
                for ref, score in refs_scores.items():
                    immu_client.VerifiedZAdd(ref, score, uuid)
            else:
                for ref, score in refs_scores.items():
                    immu_client.zAdd(ref, score, uuid)
        
            
    @classmethod
    def delete(cls, uuid: str) -> bool:
        """
            Set the object with the given uuid as deleted inside the immu database
        """
        
        # SET THE REQUEST FOR SET OBJECT AS DELETED INSIDE THE IMMU DATABASE
        deleteRequest = DeleteKeysRequest(keys=[uuid.encode()])
        
        return immu_client.delete(deleteRequest)


    @classmethod
    def get(cls, uuid_or_ref: str, only_verified: bool = False) -> dict:
        obj_dict = {}
        
        if only_verified:
            obj_data = immu_client.verifiedGet(uuid_or_ref.encode())
            
            obj_dict['verified'] = obj_data.verified
            obj_dict['timestamp'] = obj_data.timestamp
            obj_data['ref_key'] = obj_data.refkey,
        else:
            obj_data = immu_client.get(uuid_or_ref.encode())
            
        if obj_data:
            obj_dict['key'] = obj_data.key.decode()
            obj_dict['value'] = obj_data.value.decode()
            obj_dict['tx_id'] = obj_data.tx
            obj_dict['revision'] = obj_data.revision
            
            return obj_dict
        else:
            return None


    @classmethod
    def get_with_tx(cls, uuid: str, tx_id: int) -> dict:
        obj_data = immu_client.verifiedGetAt(uuid.encode(), tx_id)
        
        if obj_data:
            obj_dict = {
                'tx_id': obj_data.id,
                'key': obj_data.key.decode(),
                'value': obj_data.value.decode(),
                'verified': obj_data.verified,
                'timestamp': obj_data.timestamp,
                'ref_key': obj_data.refkey,
                'revision': obj_data.revision
            }
            return obj_dict
            

    @classmethod
    def get_keys(cls, tx_id: int) -> list[str]:
        """
            Get all objects keys that have the given transation id
        """
        
        return [key.decode() for key in immu_client.txById(tx_id)]


    @classmethod
    def after(cls, uuid: str, tx_id: int, step: int = 0) -> dict:
        obj_data = immu_client.verifiedGetSince(uuid.encode(), tx_id + step)
        
        if obj_data:
            obj_dict = {
                'tx_id': obj_data.id,
                'key': obj_data.key.decode(),
                'value': obj_data.value.decode(),
                'verified': obj_data.verified,
                'timestamp': obj_data.timestamp,
                'ref_key': obj_data.refkey,
                'revision': obj_data.revision
            }
            return obj_dict


    @classmethod
    def all(cls, size_limit: int = 1000, reverse: bool = True) -> Dict[str, str]:
        """
            Get all objects inside the immu databse
        """
        
        # Objects
        scan = immu_client.scan(b'', b'', reverse, size_limit)
        
        return {key.decode(): value.decode() for key, value in scan.items()}


    @classmethod
    def history(cls, uuid: str, 
                size_limit: int = 1000, starting_in: int = 0, 
                reverse: bool = True) -> list[dict]:
        history_data = immu_client.history(
            uuid.encode(), 
            starting_in, 
            size_limit, 
            reverse
        )
        
        return [
            {'key': data.key.decode(), 
             'value': data.value.decode(), 
             'tx': data.tx} 
            for data 
            in history_data]

    
    @classmethod
    def starts_with(cls, uuid: str = '', 
                    prefix: str = '', size_limit: int = 1000, 
                    reverse: bool = True) -> Dict[str, str]:
        """
            Get all objects that the key starts with the given prefix
        """
        
        # Objects
        scan = immu_client.scan(
            uuid.encode(), prefix.encode(), 
            reverse, size_limit
        )
        
        return {key.decode(): value.decode() for key, value in scan.items()}


    @classmethod
    def set_ref(cls, uuid: str, ref_key: str, only_verified: bool = False):
        """
            Set a ref value to a object with the given uuid
        """
        
        if only_verified:
            immu_client.verifiedSetReference(uuid.encode(), ref_key.encode())
        else:
            immu_client.setReference(uuid.encode(), ref_key.encode())
