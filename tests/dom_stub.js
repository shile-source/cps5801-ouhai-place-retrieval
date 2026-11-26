// Minimal synthetic DOM for offline interaction regression tests.
const assert = require('node:assert/strict');
class Element {
  constructor(tag = 'div') {this.tagName=tag.toUpperCase();this.children=[];this.attrs={};this.dataset={};this.events={};this.textContent='';this.value='';this.disabled=false;this.readOnly=false;}
  set innerHTML(_) {throw Error('Unsafe innerHTML used');}
  append(...nodes) {this.children.push(...nodes);}
  replaceChildren(...nodes) {this.children=[...nodes];this.textContent='';}
  setAttribute(k,v) {this.attrs[k]=String(v);}
  getAttribute(k) {return this.attrs[k] ?? null;}
  removeAttribute(k) {delete this.attrs[k];}
  get hidden() {return Object.hasOwn(this.attrs,'hidden');}
  set hidden(value) {if(value)this.attrs.hidden='';else delete this.attrs.hidden;}
  get options() {return this.children;}
  addEventListener(type, fn) {(this.events[type] ||= []).push(fn);}
  async fire(type, extra={}) {const e={target:this,preventDefault(){this.prevented=true;},...extra};for(const fn of this.events[type] || [])await fn(e);return e;}
  querySelector(selector) {assert.equal(selector,'.content');return this.content ||= new Element();}
  scrollIntoView() {}
  focus() {this.focused=true;}
  reportValidity() {this.validityReported=true;}
}

module.exports = {Element};
