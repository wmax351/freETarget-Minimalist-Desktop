(()=>{
'use strict';
const boot=/*__FT_DESKTOP_BOOT__*/;
const cache=new Map(Object.entries(boot.storage));let revision=boot.revision;
function report(error){window.dispatchEvent(new CustomEvent('ft-storage-error',{detail:error.message}));return error}
function change(key,value,remove=false){
 const request=new XMLHttpRequest();request.open('POST','/desktop/store',false);request.setRequestHeader('Content-Type','application/json');request.setRequestHeader('X-FT-Session',boot.token);
 try{request.send(JSON.stringify({key,value,remove,expected_revision:revision}))}catch(error){throw report(Error('The desktop data service is unavailable. Keep the app open and try again.'))}
 let result;try{result=JSON.parse(request.responseText)}catch{throw report(Error('The local data service returned an invalid response.'))}
 if(request.status<200||request.status>=300)throw report(Error(result.error||'Local data could not be saved.'));
 revision=result.revision;
 if(remove)cache.delete(key);else cache.set(key,value);
}
const storage={getItem:key=>cache.has(String(key))?cache.get(String(key)):null,setItem(key,value){key=String(key);value=String(value);if(cache.get(key)===value&&cache.has(key))return;change(key,value)},removeItem(key){key=String(key);if(cache.has(key))change(key,null,true)},key:index=>Array.from(cache.keys())[index]??null,get length(){return cache.size}};
Object.freeze(storage);window.FTDesktopStorage=storage;
const originalFetch=window.fetch.bind(window);
window.fetch=(input,options={})=>{
 const address=new URL(typeof input==='string'?input:input.url,window.location.href);
 if(address.origin!==boot.origin)return Promise.reject(Error('External requests are not part of the desktop data service.'));
 const headers=new Headers(options.headers||(typeof input==='object'?input.headers:undefined));headers.set('X-FT-Session',boot.token);
 return originalFetch(input,{...options,headers,credentials:'same-origin'});
};
window.FTDesktop={acceptAppleSync(next,values){if(!Number.isInteger(next)||next!==revision+1)throw Error("Local data changed. Reload to see synced records.");revision=next;for(const [key,value] of Object.entries(values))cache.set(key,value)},async request(path,body={}){const response=await window.fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await response.json();if(!response.ok)throw Error(data.error||'Desktop operation failed.');return data},get revision(){return revision}};
})();
