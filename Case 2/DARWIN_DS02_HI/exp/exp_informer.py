# -*- coding: utf-8 -*-
####DARWIN HI DS02 
import os
import torch
import numpy as np
import pandas as pd
from models.model import Informer, InformerStack,BiLSTM,DCNN,DH_1,TransGCU#,DeepHealth
from exp.exp_basic import Exp_Basic
from datapreprocess import DataPreproserse
from dataloader import DataReader
from utils.tools import EarlyStopping, adjust_learning_rate
from utils.metrics import metric
import torch.nn as nn
from torch import optim
from torch.utils.data import DataLoader
import os
import time
import warnings
import h5py
warnings.filterwarnings('ignore')

class Exp_Informer(Exp_Basic):
    def __init__(self, args):
        super(Exp_Informer, self).__init__(args)
        self.args = args
        
        
        self._datapreproserse_()  
        

    def _datapreproserse_(self):
        args = self.args
        datapreproserse = DataPreproserse(                       
                    root_path=args.root_path,
                    data_path=args.data_path,
                    dataset_name=args.dataset_name,
                    validation_split=args.validation_split,
                    normal_style=args.normal_style,
                    down_sampling=args.down_sampling,
                    down_sampling_rate=args.down_sampling_rate,
                    ag_data_len=args.ag_data_len,          
                    ag_seq_len=args.ag_seq_len,
                    stride=args.stride,
                    seq_len=args.seq_len,
                    label_len=args.label_len,
                    pred_len=args.pred_len,
                    is_padding=args.is_padding,
                    data_augmentation=args.data_augmentation,
                    rate_data=args.rate_data,
                    synthetic_data_path=args.synthetic_data_path,       
                     )
        
        self.train_enc, self.train_dec, self.val_enc, self.val_dec, self.test_enc, self.test_dec = datapreproserse.process()
        
        
    def _build_model(self):

        model_dict = {
            'DARWIN':Informer,
            'informer':Informer,
            'informerstack':InformerStack,
            'biLSTM':BiLSTM,
            'dcnn':DCNN,
            'transgcu':TransGCU,
            'dh_1':DH_1,
            #'deephealth':DeepHealth,
        }
        
        if self.args.model in ['informer','informerstack','DARWIN']:
            e_layers = self.args.e_layers if self.args.model in ['informer','DARWIN'] else self.args.s_layers
            model = model_dict[self.args.model](
                self.args.enc_in,
                self.args.dec_in, 
                self.args.c_out, 
                self.args.seq_len, 
                self.args.label_len,
                self.args.pred_len, 
                self.args.is_perception,
                self.args.factor,
                self.args.d_model, 
                self.args.n_heads, 
                e_layers, # self.args.e_layers,
                self.args.d_layers, 
                self.args.d_ff,
                self.args.dropout, 
                self.args.attn,
                self.args.embed,
                self.args.freq,
                self.args.activation,
                self.args.output_attention,
                self.args.distil,
                self.args.mix,
                self.device
            ).float()
                
        elif self.args.model == 'biLSTM':
            model = model_dict[self.args.model](input_size=self.args.enc_in,hidden_size=512,
                                                num_layers=5,output_size=self.args.c_out,seq_len=self.args.seq_len,
                                                out_len=self.args.pred_len).float() #hidden_size=512,num_layers=5
            
        elif self.args.model == 'dcnn':
            model = model_dict[self.args.model](pred_len=self.args.pred_len).float()
        
        elif self.args.model=='transgcu':
            e_layers = self.args.e_layers if self.args.model=='transgcu' else self.args.s_layers
            model = model_dict[self.args.model](
                self.args.enc_in,
                self.args.dec_in, 
                self.args.c_out, 
                self.args.seq_len, 
                self.args.label_len,
                self.args.pred_len, 
                self.args.is_perception,
                self.args.factor,
                self.args.d_model, 
                self.args.n_heads, 
                e_layers, # self.args.e_layers,
                self.args.d_layers, 
                self.args.d_ff,
                self.args.dropout, 
                self.args.attn,
                self.args.embed,
                self.args.freq,
                self.args.activation,
                self.args.output_attention,
                self.args.distil,
                self.args.mix,
                self.device
            ).float()
            
            
        elif self.args.model=='dh_1':
            e_layers = self.args.e_layers if self.args.model=='dh_1' else self.args.s_layers
            model = model_dict[self.args.model](
                self.args.enc_in,
                self.args.dec_in, 
                self.args.c_out, 
                self.args.seq_len, 
                self.args.label_len,
                self.args.pred_len, 
                self.args.is_perception,
                self.args.factor,
                self.args.d_model, 
                self.args.n_heads, 
                e_layers, # self.args.e_layers,
                self.args.d_layers, 
                self.args.d_ff,
                self.args.dropout, 
                self.args.attn,
                self.args.embed,
                self.args.freq,
                self.args.activation,
                self.args.output_attention,
                self.args.distil,
                self.args.mix,
                self.device
            ).float()
            
                   
            
        if self.args.use_multi_gpu and self.args.use_gpu:
            model = nn.DataParallel(model, device_ids=self.args.device_ids)
            
        return model
    
        

    def _get_data(self, flag):
        args = self.args
             
        if flag == 'test':       
            shuffle_flag = False; drop_last = True; batch_size = args.batch_size; freq=args.detail_freq   
        elif flag=='pred':   
            shuffle_flag = False; drop_last = False; batch_size = args.batch_size; freq=args.detail_freq
        elif flag in ['train','val']: 
            shuffle_flag = True; drop_last = True; batch_size = args.batch_size; freq=args.freq
       
    
        data_set = DataReader(         
                    train_enc=self.train_enc,
                    train_dec=self.train_dec,
                    val_enc=self.val_enc,
                    val_dec=self.val_dec,
                    test_enc=self.test_enc,
                    test_dec=self.test_dec,
                    flag=flag,   
                    )
        
        data_loader = DataLoader(
            data_set,
            batch_size=batch_size,
            shuffle=shuffle_flag,
            num_workers=args.num_workers,
            drop_last=drop_last)

        return data_set, data_loader
    

    def _select_optimizer(self):
        model_optim = optim.Adam(self.model.parameters(), lr=self.args.learning_rate)
        return model_optim
    
    def _select_criterion(self):
        if self.args.loss == 'mse':
            criterion =  nn.MSELoss()
        elif self.args.loss == 'mae':
            criterion =  nn.L1Loss()
        return criterion
    

    def vali(self, vali_data, vali_loader, criterion):
        self.model.eval()
        total_loss = []

        for i, (batch_x,batch_y,) in enumerate(vali_loader):
            
            if self.args.output_attention:
                pred, true,attn_weights = self._process_one_batch(vali_data, batch_x, batch_y)
            else:
                pred, true = self._process_one_batch(vali_data, batch_x, batch_y)
                     
            #loss = criterion(pred.detach().cpu(), true.detach().cpu())    ###loss.detach().cpu(), else cuda out memory
            if self.args.is_perception == False:
                loss = criterion(pred.detach().cpu(), true.detach().cpu())
            elif self.args.is_perception == True:
                loss = criterion(pred[:,-self.args.seq_len:,:].detach().cpu(), true[:,-self.args.seq_len:,:].detach().cpu())
                            
            total_loss.append(loss)
            
        #AttributeError: 'torch.dtype' object has no attribute 'type'    
        #total_loss = np.average(total_loss)
        total_loss = torch.mean(torch.stack(total_loss))
        
        self.model.train()
        return total_loss
    

    def train(self, setting):
        train_data, train_loader = self._get_data(flag='train')
        vali_data, vali_loader = self._get_data(flag='val')      
        
        path = os.path.join(self.args.checkpoints, setting)
        if not os.path.exists(path):
            os.makedirs(path)

        time_now = time.time()
        
        train_steps = len(train_loader)
        early_stopping = EarlyStopping(patience=self.args.patience, verbose=True)
        
        model_optim = self._select_optimizer()
        criterion =  self._select_criterion()

        if self.args.use_amp:
            scaler = torch.cuda.amp.GradScaler()

        for epoch in range(self.args.train_epochs):
            iter_count = 0
            train_loss = []
            
            self.model.train()
            epoch_time = time.time()
            for i, (batch_x,batch_y) in enumerate(train_loader):
                iter_count += 1
                
                model_optim.zero_grad() 
                
                if self.args.output_attention:
                    pred, true,attn_weights = self._process_one_batch(train_data, batch_x, batch_y)
                else:        
                    pred, true = self._process_one_batch(train_data, batch_x, batch_y)
                
                
                if self.args.is_perception == False:
                    loss = criterion(pred, true)
                elif self.args.is_perception == True:
                    loss = criterion(pred[:,-self.args.seq_len:,:], true[:,-self.args.seq_len:,:])
            
                train_loss.append(loss.item())
                
                if (i+1) % 100==0:
                    print("\titers: {0}, epoch: {1} | loss: {2:.7f}".format(i + 1, epoch + 1, loss.item()))
                    speed = (time.time()-time_now)/iter_count
                    left_time = speed*((self.args.train_epochs - epoch)*train_steps - i)
                    print('\tspeed: {:.4f}s/iter; left time: {:.4f}s'.format(speed, left_time))
                    iter_count = 0
                    time_now = time.time()
                
                if self.args.use_amp:
                    scaler.scale(loss).backward()
                    scaler.step(model_optim)
                    scaler.update()
                else:
                    loss.backward()
                    model_optim.step()

            ##########################
            #del train_data, train_loader 
            
            print("Epoch: {} cost time: {}".format(epoch+1, time.time()-epoch_time))
            train_loss = np.average(train_loss)
            vali_loss = self.vali(vali_data, vali_loader, criterion)
            
            ##########################
            #del vali_data, vali_loader

            
            print("Epoch: {0}, Steps: {1} | Train Loss: {2:.7f} Vali Loss: {3:.7f} ".format(
                epoch + 1, train_steps, train_loss, vali_loss))
            early_stopping(vali_loss, self.model, path)
            if early_stopping.early_stop:
                print("Early stopping")
                break

            adjust_learning_rate(model_optim, epoch+1, self.args)
            
        best_model_path = path+'/'+'checkpoint.pth'
        self.model.load_state_dict(torch.load(best_model_path))
        
        return self.model

    
    
    def test(self, setting):
        test_data, test_loader = self._get_data(flag='test')    
        self.model.eval()

        preds,trues  = [],[]
        
        for i, (batch_x,batch_y) in enumerate(test_loader):
            
            if self.args.output_attention:
                pred, true,attn_weights = self._process_one_batch(test_data, batch_x, batch_y)
            else:
                pred, true = self._process_one_batch(test_data, batch_x, batch_y)
           
            preds.append(pred.detach().cpu().numpy())
            trues.append(true.detach().cpu().numpy())
        
        ##########################
        del test_data, test_loader
        
        preds = np.array(preds)
        trues = np.array(trues)

        print('test shape:', preds.shape, trues.shape)
        preds = preds.reshape(-1, preds.shape[-2], preds.shape[-1])
        trues = trues.reshape(-1, trues.shape[-2], trues.shape[-1])
        print('test shape:', preds.shape, trues.shape) 
        
        # result save
        folder_path = self.args.root_path + '/results/' + setting +'/'
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        mae, mse, rmse, mape, mspe = metric(preds, trues)
        
        # mae, mse, rmse, mape, mspe = metric(preds, preds)
        print('mse:{}, mae:{}'.format(mse, mae))
        np.save(folder_path+'metrics_test.npy', np.array([mae, mse, rmse, mape, mspe]))
        if self.args.output_attention:
            np.save(folder_path+'attn_weights.npy', attn_weights)   

        # Create a new file hdf5 dataset
        f = h5py.File(folder_path +'{}_DS02_{}_rate{}_ag{}.h5'.format(self.args.model,self.args.down_sampling,\
                                                                        self.args.down_sampling_rate,self.args.data_augmentation), 'w')
        f.create_dataset('trues', data=np.arange(trues.all()))
        f.create_dataset('preds', data=np.arange(preds.all()))
        f.close()
        
        del trues, preds
        return
    

    def predict(self, setting, load=False):
        pred_data, pred_loader = self._get_data(flag='pred')
        
        if load:
            path = os.path.join(self.args.checkpoints, setting)
            best_model_path = path+'/'+'checkpoint.pth'
            self.model.load_state_dict(torch.load(best_model_path))

        self.model.eval()
        
        preds = []
        
        for i, (batch_x,batch_y) in enumerate(pred_loader):
            
            if self.args.output_attention:
                pred, true,attn_weights = self._process_one_batch(pred_data, batch_x, batch_y)
            else:
                pred, true = self._process_one_batch(pred_data, batch_x, batch_y)
            
            
            preds.append(pred.detach().cpu().numpy())

        preds = np.array(preds)
        preds = preds.reshape(-1, preds.shape[-2], preds.shape[-1])
        
        # result save
        folder_path = 'hi/results/' + setting +'/'
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)       
        np.save(folder_path+'real_prediction.npy', preds)
        return

    def _process_one_batch(self, dataset_object, batch_x, batch_y):
        if self.args.model in ['DARWIN','informer' ,'informerstack' ,'transgcu']:
            batch_x = batch_x.float().to(self.device)
            batch_y = batch_y.float()  #后面还要处理 再self.device?
            batch_x = batch_x[:,:,:-1]    #delect HI
        

            # decoder input
            if self.args.padding==0:
                dec_inp = torch.zeros([batch_y.shape[0], self.args.pred_len, batch_y.shape[-1]]).float()
            elif self.args.padding==1:
                dec_inp = torch.ones([batch_y.shape[0], self.args.pred_len, batch_y.shape[-1]]).float()
            
            dec_inp = torch.cat([batch_y[:,:self.args.label_len,:], dec_inp], dim=1).float().to(self.device)
            dec_inp = dec_inp.float()[:,:,:-1]   #delect HI

            # encoder - decoder
            if self.args.use_amp:
                with torch.cuda.amp.autocast():
                    if self.args.output_attention:
                        outputs = self.model(batch_x,  dec_inp)[0]
                        attn_weights = self.model(batch_x,  dec_inp)[1]
                    else:
                        outputs = self.model(batch_x,  dec_inp)
            else:
                if self.args.output_attention:
                    outputs = self.model(batch_x,  dec_inp)[0]
                    attn_weights = self.model(batch_x,  dec_inp)[1]
                else:
                    outputs = self.model(batch_x,  dec_inp)
            if self.args.inverse:
                outputs = dataset_object.inverse_transform(outputs)


            #batch_y is correspond groud_truth
            if self.args.features =='MS' or self.args.features =='S':
                if self.args.is_perception == False:
                    batch_y = batch_y[:,-self.args.pred_len:,-1:].to(self.device)     #the last column is HI
                elif self.args.is_perception == True:
                    batch_y = batch_y[:,(-self.args.pred_len-self.args.label_len):,-1:].to(self.device) 

            elif self.args.features =='M':
                if self.args.is_perception == False:
                    batch_y = batch_y[:,-self.args.pred_len:,:-1].to(self.device)     #remain sensor, exclude HI
                elif self.args.is_perception == True:
                    batch_y = batch_y

            if self.args.output_attention:
                return outputs, batch_y,attn_weights
            else:
                return outputs, batch_y

        elif self.args.model == 'biLSTM':
            batch_x = batch_x.float().to(self.device)
            batch_y = batch_y.float()[:,-self.args.pred_len:,-1:].to(self.device)

            ###小志添加 
            batch_x = batch_x.float()[:,:,:-1]   #delect HI
            outputs = self.model(batch_x)
            
            if self.args.inverse:
                outputs = dataset_object.inverse_transform(outputs)

            return outputs, batch_y
        
        
        elif self.args.model == 'dcnn':
            batch_x = batch_x.float().to(self.device)
            batch_y = batch_y.float()[:,-self.args.pred_len:,-1:].to(self.device)

            batch_x = batch_x.float()[:,:,:-1]   #delect HI
            batch_x = batch_x.unsqueeze(1) #32*48*14 --> 32*1*48*14            
            outputs = self.model(batch_x)
                
            if self.args.inverse:
                outputs = dataset_object.inverse_transform(outputs)
            
            return outputs, batch_y
